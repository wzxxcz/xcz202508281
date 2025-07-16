#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

# 禁用所有警告
urllib3.disable_warnings()

# 专业级配置
PHASE1_WORKERS = 30       # 连接测试并发数
PHASE2_WORKERS = 10       # 流畅度测试并发数
CONN_TIMEOUT = 5          # 连接测试超时(秒)
STREAM_TIMEOUT = 10       # 流畅度测试时长(秒)
MIN_BITRATE = 300         # 最低流畅比特率(kbps)
PROGRESS_INTERVAL = 20    # 进度显示间隔

class ProfessionalTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept-Encoding': 'gzip'
        })

    def phase1_connection_test(self, url):
        """5秒专业连接测试"""
        try:
            # 双重检测机制
            try:
                resp = self.session.head(url, timeout=2, allow_redirects=True)
                if resp.status_code == 200:
                    return True, "HEAD检测通过"
            except:
                pass
            
            with self.session.get(url, stream=True, timeout=CONN_TIMEOUT) as resp:
                if resp.status_code == 200:
                    # 读取前512字节确认有效性
                    next(resp.iter_content(512))
                    return True, "GET检测通过"
                return False, f"HTTP状态码:{resp.status_code}"
        except Exception as e:
            return False, f"连接错误:{str(e)}"

    def phase2_stream_test(self, url):
        """10秒专业流畅度测试"""
        try:
            start_time = time.time()
            total_bytes = 0
            freeze_count = 0
            last_chunk_time = start_time
            
            with self.session.get(url, stream=True, timeout=STREAM_TIMEOUT+2) as resp:
                if resp.status_code != 200:
                    return False, "HTTP错误"
                
                # 实时流分析
                for chunk in resp.iter_content(4096):
                    now = time.time()
                    if chunk:  # 有效数据块
                        total_bytes += len(chunk)
                        chunk_gap = now - last_chunk_time
                        if chunk_gap > 1.0:  # 超过1秒无数据视为卡顿
                            freeze_count += 1
                        last_chunk_time = now
                    
                    if now - start_time > STREAM_TIMEOUT:
                        break
            
            duration = now - start_time
            if duration < 5:  # 最少需要5秒有效数据
                return False, "测试时长不足"
            
            # 综合评估
            bitrate = (total_bytes * 8) / (duration * 1000)  # 计算kbps
            if bitrate < MIN_BITRATE:
                return False, f"比特率不足({int(bitrate)}kbps)"
            if freeze_count >= 3:
                return False, f"卡顿次数({freeze_count}次)"
            
            return True, f"流畅(比特率:{int(bitrate)}kbps, 卡顿:{freeze_count}次)"
        except Exception as e:
            return False, f"流畅度错误:{str(e)}"

def load_channels(file_path):
    """高效文件读取"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip().split(',', 1) for line in f 
               if line.strip() and ',' in line and not line.startswith('#')]

def run_professional_test(input_file):
    if not os.path.exists(input_file):
        print("❌ 错误：文件不存在")
        return
    
    base_name = os.path.splitext(input_file)[0]
    conn_file = f"{base_name}_有效连接.txt"
    stream_file = f"{base_name}_流畅源.txt"
    report_file = f"{base_name}_专业报告.txt"
    
    channels = load_channels(input_file)
    total = len(channels)
    print(f"🔍 开始专业级测试 | 总数: {total} | 阶段1: {CONN_TIMEOUT}秒x{PHASE1_WORKERS}线程 | 阶段2: {STREAM_TIMEOUT}秒x{PHASE2_WORKERS}线程")
    start_time = time.time()
    
    # 阶段1：连接测试
    print("\n📡 阶段1 - 连接测试(5秒)...")
    valid_conn = []
    tester = ProfessionalTester()
    
    with ThreadPoolExecutor(max_workers=PHASE1_WORKERS) as executor:
        futures = {executor.submit(tester.phase1_connection_test, url): (idx, name) 
                 for idx, (name, url) in enumerate(channels, 1)}
        
        for future in as_completed(futures):
            idx, name = futures[future]
            try:
                is_valid, reason = future.result()
                if is_valid:
                    valid_conn.append((name, channels[idx-1][1], reason))
                
                if idx % PROGRESS_INTERVAL == 0 or idx == total:
                    elapsed = time.time() - start_time
                    print(f"\r进度: {idx}/{total} | 有效: {len(valid_conn)} | 耗时: {elapsed:.1f}s", end='')
            except:
                pass
    
    # 保存阶段1结果
    with open(conn_file, 'w', encoding='utf-8') as f:
        f.write("\n".join([f"{name},{url}" for name, url, _ in valid_conn]))
    
    # 阶段2：流畅度测试
    print("\n\n📺 阶段2 - 流畅度测试(10秒)...")
    valid_stream = []
    phase2_start = time.time()
    
    with ThreadPoolExecutor(max_workers=PHASE2_WORKERS) as executor:
        futures = {executor.submit(tester.phase2_stream_test, url): (idx, name, url) 
                 for idx, (name, url, _) in enumerate(valid_conn, 1)}
        
        for future in as_completed(futures):
            idx, name, url = futures[future]
            try:
                is_valid, reason = future.result()
                if is_valid:
                    valid_stream.append((name, url, reason))
                
                if idx % PROGRESS_INTERVAL == 0 or idx == len(valid_conn):
                    elapsed = time.time() - phase2_start
                    remain = (len(valid_conn) - idx) * (elapsed / idx) if idx > 0 else 0
                    print(f"\r进度: {idx}/{len(valid_conn)} | 流畅: {len(valid_stream)} | 剩余: {remain:.1f}s", end='')
            except:
                pass
    
    # 生成专业报告
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=== 专业测试报告 ===\n")
        f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总频道数: {total}\n")
        f.write(f"有效连接: {len(valid_conn)}\n")
        f.write(f"流畅频道: {len(valid_stream)}\n")
        f.write(f"流畅率: {len(valid_stream)/len(valid_conn)*100:.1f}%\n\n")
        
        f.write("=== 流畅频道详情 ===\n")
        for name, url, reason in valid_stream[:100]:  # 最多显示100个
            f.write(f"{name} | {reason}\n")
    
    # 保存最终结果
    with open(stream_file, 'w', encoding='utf-8') as f:
        f.write("\n".join([f"{name},{url}" for name, url, _ in valid_stream]))
    
    print(f"\n\n✅ 测试完成！")
    print(f"📶 有效连接: {len(valid_conn)}/{total}")
    print(f"🎬 流畅频道: {len(valid_stream)}/{len(valid_conn)}")
    print(f"💾 有效连接: {conn_file}")
    print(f"🎥 流畅源: {stream_file}")
    print(f"📊 专业报告: {report_file}")
    print(f"⏱️ 总耗时: {time.time()-start_time:.1f}秒")

if __name__ == '__main__':
    print("="*50)
    print("📺 直播源专业测试工具")
    print("="*50)
    input_file = input("📂 输入文件路径(默认: 采集.txt): ") or "采集.txt"
    run_professional_test(input_file)
