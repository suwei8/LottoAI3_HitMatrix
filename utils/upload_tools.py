import os
import subprocess
import shlex

def run_command(cmd, capture=False, use_shell=False):
    print(f"\n🟢 执行: {cmd}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    if capture:
        if use_shell:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                env=env
            )
        else:
            result = subprocess.run(
                cmd if isinstance(cmd, list) else shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                env=env
            )
    else:
        if use_shell:
            result = subprocess.run(cmd, shell=True, env=env)
        else:
            result = subprocess.run(cmd if isinstance(cmd, list) else shlex.split(cmd), env=env)

    if result.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
        print("命令输出：", result.stdout)
        sys.exit(result.returncode)
    return result


def do_final_dump_and_upload(playtype_en):
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
    BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD")

    dump_cmd = (
        f"mysqldump -h {MYSQL_HOST} -u{MYSQL_USER} -p\"{MYSQL_PASSWORD}\" "
        f"{MYSQL_DATABASE} tasks best_tasks best_ranks > tasks_best.sql"
    )

    zip_name = f"lotto_ai3_hitmatrix_p5_{playtype_en}.sql.zip"
    zip_cmd = f"zip -P {BACKUP_PASSWORD} {zip_name} tasks_best.sql"

    run_command(dump_cmd, use_shell=True)
    run_command(zip_cmd, use_shell=True)

    create_cmd = (
        f"gh release create p5_{playtype_en} "
        f"--repo suwei8/LottoAI3_HitMatrix_date "
        f"--title 'p5_{playtype_en}' || echo 'Release already exists'"
    )
    run_command(create_cmd, use_shell=True)

    upload_cmd = (
        f"gh release upload p5_{playtype_en} {zip_name} "
        f"--clobber --repo suwei8/LottoAI3_HitMatrix_date"
    )
    run_command(upload_cmd, use_shell=True)
