"""
웹 IDE Pod 리소스 상태 진단 스크립트
CPU / GPU / 메모리 / 컨테이너 리소스 제한(cgroup)까지 확인
사용법: python check_resources.py
"""

import subprocess
import os
import platform


def section(title):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def run_cmd(cmd, timeout=5):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# ---------------------------------------------------------
# 1. CPU 정보
# ---------------------------------------------------------
def check_cpu():
    section("1. CPU 정보")
    print(f"플랫폼: {platform.platform()}")
    print(f"프로세서: {platform.processor() or 'N/A'}")
    print(f"논리 코어 수 (os.cpu_count): {os.cpu_count()}")

    try:
        import psutil
        print(f"물리 코어 수: {psutil.cpu_count(logical=False)}")
        print(f"현재 CPU 사용률: {psutil.cpu_percent(interval=1)}%")
        freq = psutil.cpu_freq()
        if freq:
            print(f"CPU 주파수: {freq.current:.0f} MHz (max: {freq.max:.0f} MHz)")
    except ImportError:
        print("(psutil 미설치 - 'pip install psutil' 하면 더 상세히 볼 수 있음)")


# ---------------------------------------------------------
# 2. 메모리 정보
# ---------------------------------------------------------
def check_memory():
    section("2. 메모리 정보")
    try:
        import psutil
        vm = psutil.virtual_memory()
        print(f"전체: {vm.total / (1024**3):.2f} GB")
        print(f"사용중: {vm.used / (1024**3):.2f} GB ({vm.percent}%)")
        print(f"가용: {vm.available / (1024**3):.2f} GB")
    except ImportError:
        meminfo = run_cmd(["cat", "/proc/meminfo"])
        if meminfo:
            for line in meminfo.splitlines()[:3]:
                print(line)


# ---------------------------------------------------------
# 3. 컨테이너(cgroup) 리소스 제한 - K8s Pod에서 실제 할당된 limit 확인
# ---------------------------------------------------------
def check_cgroup_limits():
    section("3. 컨테이너 리소스 제한 (YAML에서 설정한 limits/requests 반영값)")

    # cgroup v2
    cpu_max = run_cmd(["cat", "/sys/fs/cgroup/cpu.max"])
    mem_max = run_cmd(["cat", "/sys/fs/cgroup/memory.max"])

    # cgroup v1 (fallback)
    if cpu_max is None:
        quota = run_cmd(["cat", "/sys/fs/cgroup/cpu/cpu.cfs_quota_us"])
        period = run_cmd(["cat", "/sys/fs/cgroup/cpu/cpu.cfs_period_us"])
        if quota and period and quota != "-1":
            cpu_max = f"{quota} {period} (v1, quota/period)"
        mem_max = run_cmd(["cat", "/sys/fs/cgroup/memory/memory.limit_in_bytes"])

    if cpu_max:
        print(f"CPU limit (cgroup): {cpu_max}")
    else:
        print("CPU limit: 확인 불가 (cgroup 미마운트 또는 제한 없음)")

    if mem_max:
        try:
            mem_bytes = int(mem_max.split()[0])
            print(f"Memory limit (cgroup): {mem_bytes / (1024**3):.2f} GB")
        except (ValueError, IndexError):
            print(f"Memory limit (cgroup): {mem_max}")
    else:
        print("Memory limit: 확인 불가")


# ---------------------------------------------------------
# 4. GPU 정보 (nvidia-smi 상세 + torch)
# ---------------------------------------------------------
def check_gpu():
    section("4. GPU 정보")

    smi_out = run_cmd([
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,driver_version",
        "--format=csv,noheader,nounits"
    ])

    has_gpu = smi_out is not None and smi_out != ""

    if has_gpu:
        print("[nvidia-smi] GPU 감지됨\n")
        print(f"{'idx':<4}{'name':<25}{'mem_used/total(MB)':<22}{'util(%)':<10}{'temp(C)':<8}")
        for line in smi_out.splitlines():
            idx, name, mem_total, mem_used, mem_free, util, temp, driver = [x.strip() for x in line.split(",")]
            print(f"{idx:<4}{name:<25}{mem_used+'/'+mem_total:<22}{util:<10}{temp:<8}")
        print(f"\n드라이버 버전: {driver}")
    else:
        print("[nvidia-smi] 실행 불가 → GPU가 붙어있지 않은 환경 (CPU-only)")

    # NVIDIA_VISIBLE_DEVICES 같은 K8s 주입 환경변수
    env_keys = ["NVIDIA_VISIBLE_DEVICES", "CUDA_VISIBLE_DEVICES", "NVIDIA_DRIVER_CAPABILITIES"]
    env_found = {k: os.environ.get(k) for k in env_keys if os.environ.get(k)}
    if env_found:
        print(f"\nGPU 관련 환경변수: {env_found}")

    # torch 있으면 추가 확인
    try:
        import torch
        print(f"\n[torch] CUDA 사용 가능: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                print(f"  - device {i}: {torch.cuda.get_device_name(i)}")
    except ImportError:
        pass

    return has_gpu


# ---------------------------------------------------------
# 5. 결론
# ---------------------------------------------------------
def main():
    check_cpu()
    check_memory()
    check_cgroup_limits()
    has_gpu = check_gpu()

    section("결론")
    if has_gpu:
        print("✅ 이 IDE 환경은 GPU가 할당된 Pod 입니다.")
    else:
        print("⚪ 이 IDE 환경은 CPU-only Pod 입니다.")
    print()


if __name__ == "__main__":
    main()
