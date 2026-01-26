import time
import math
import multiprocessing
import os
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich import box

# --- CORE LOGIC (Ported from workerCode in index.html) ---
def is_prime(num):
    if num < 2: return False
    if num == 2: return True
    if num % 2 == 0: return False
    
    limit = int(math.isqrt(num))
    for i in range(3, limit + 1, 2):
        if num % i == 0:
            return False
    return True

def worker_process(worker_id, stride, queue, stop_event):
    """
    Replicates the JS worker logic:
    - Starts at 100 + id
    - Uses specific 'growth' factor: floor(current * 0.00000005)
    - Runs in time slices to prevent locking, reporting back periodically.
    """
    current_num = 100 + worker_id
    
    while not stop_event.is_set():
        count = 0
        max_found = 0
        start_time = time.time()
        
        # Run for approx 0.2 seconds (matching the 200ms JS interval)
        # to batch updates and reduce Queue overhead.
        while (time.time() - start_time) < 0.2:
            if is_prime(current_num):
                count += 1
                max_found = current_num
            
            # --- LOGIC PORT ---
            # "Smooth Decay" math from index.html
            growth = math.floor(current_num * 0.00000005)
            current_num += (stride + growth)
        
        # Report results for this slice
        if count > 0 or max_found > 0:
            queue.put({
                'id': worker_id, 
                'count': count, 
                'highest': max_found
            })

# --- UI LAYOUT ---
def generate_layout(stats):
    layout = Layout()
    
    # Header
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1)
    )
    
    # Header Content
    status_style = "bold green" if stats['running'] else "bold red"
    status_text = "RUNNING" if stats['running'] else "PAUSED"
    header_content = Table.grid(expand=True)
    header_content.add_column(justify="left")
    header_content.add_column(justify="right")
    header_content.add_row(
        "[bold yellow]⚡ PrimeNode Analytics[/] (CLI Edition)",
        f"[{status_style}]● {status_text}[/]"
    )
    layout["header"].update(Panel(header_content, style="white on #0f172a"))
    
    # Grid for metrics
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    # Left Column: Metrics
    metrics_table = Table(box=None, expand=True)
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", justify="right", style="bold white")
    
    metrics_table.add_row("Primes Verified", f"{stats['total']:,}")
    metrics_table.add_row("Velocity (p/s)", f"{stats['speed']:,}")
    metrics_table.add_row("Highest Prime", f"{stats['highest']:,}")
    metrics_table.add_row("Active Threads", str(stats['threads']))
    
    layout["left"].update(
        Panel(metrics_table, title="System Overview", border_style="blue")
    )

    # Right Column: "Charts" (Simulated with text bars)
    # Replicating the "Speed Chart" and "Growth Chart" conceptually
    history_table = Table(box=box.SIMPLE, expand=True, show_header=False)
    history_table.add_column("Type", style="dim")
    history_table.add_column("Visual", ratio=1)
    
    # Simple visualizer for speed
    max_visual_len = 30
    
    # Speed Bar
    # Normalize speed for visualization (arbitrary scale for CLI demo)
    speed_bar_len = min(int((stats['speed'] / 5000) * max_visual_len), max_visual_len) if stats['speed'] else 0
    speed_vis = "█" * speed_bar_len
    
    history_table.add_row("Speed", f"[#6366f1]{speed_vis}[/]")
    history_table.add_row("Growth", f"[#10b981]{'█' * (speed_bar_len // 2)}[/]") # Abstract representation
    
    layout["right"].update(
        Panel(history_table, title="Real-time Analytics", border_style="green")
    )
    
    return layout

# --- MAIN EXECUTION ---
def main():
    # Configuration
    CORE_COUNT = multiprocessing.cpu_count()
    
    # State
    queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()
    workers = []
    
    stats = {
        'total': 0,
        'speed': 0,
        'highest': 0,
        'threads': CORE_COUNT,
        'running': True
    }
    
    last_check_time = time.time()
    last_total_primes = 0
    
    # Start Workers
    for i in range(CORE_COUNT):
        p = multiprocessing.Process(
            target=worker_process, 
            args=(i, CORE_COUNT, queue, stop_event)
        )
        p.start()
        workers.append(p)
        
    console = Console()
    
    try:
        with Live(generate_layout(stats), refresh_per_second=4, screen=True) as live:
            while True:
                # Process all messages currently in queue
                while not queue.empty():
                    data = queue.get()
                    stats['total'] += data['count']
                    if data['highest'] > stats['highest']:
                        stats['highest'] = data['highest']
                
                # Update Velocity every 1 second
                now = time.time()
                if now - last_check_time >= 1.0:
                    stats['speed'] = stats['total'] - last_total_primes
                    last_total_primes = stats['total']
                    last_check_time = now
                
                live.update(generate_layout(stats))
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        # Graceful shutdown
        stop_event.set()
        for p in workers:
            p.terminate()
        print("\nNode Stopped.")

if __name__ == "__main__":
    multiprocessing.freeze_support() # Windows support
    main()
