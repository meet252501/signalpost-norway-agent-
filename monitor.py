import time
import sys
import os

log_file = r"C:\Users\Meet Sutariya\.gemini\antigravity-ide\brain\3b16b31f-808b-4037-97ec-7da68e00b2a6\.system_generated\tasks\task-4797.log"

print("\n\033[96m" + "="*60 + "\033[0m")
print("\033[1;97m SIGNALPOST EXTERNAL EVALUATION MONITOR\033[0m")
print("\033[96m" + "="*60 + "\033[0m\n")

stages = [
    "Running foundation batch",
    "google_news_rss_exact_title_experiment_v1",
    "yt_dlp_exact_channel_search_v1",
    "fagfolkguiden_embedded_google_reviews_experiment_v1",
    "official_annual_report_workforce_v1",
    "Done! All artifacts generated"
]

current_stage = 0
spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
spinner_idx = 0

try:
    while current_stage < len(stages):
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            new_stage = current_stage
            for i, stage in enumerate(stages):
                if stage in content:
                    new_stage = max(new_stage, i + 1)
            
            current_stage = new_stage
            
        progress = int((current_stage / len(stages)) * 40)
        bar = "█" * progress + "░" * (40 - progress)
        percent = int((current_stage / len(stages)) * 100)
        
        status = stages[current_stage] if current_stage < len(stages) else "Completed!"
        
        sys.stdout.write(f"\r\033[92m[{bar}]\033[0m {percent}% | {spinner[spinner_idx]} \033[93m{status[:30].ljust(30)}\033[0m")
        sys.stdout.flush()
        
        spinner_idx = (spinner_idx + 1) % len(spinner)
        time.sleep(0.1)

    print("\n\n\033[92m✔ Evaluation completed successfully!\033[0m")
except KeyboardInterrupt:
    pass
