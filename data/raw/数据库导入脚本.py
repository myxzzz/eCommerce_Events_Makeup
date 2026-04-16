import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ================= Configuration / 配置 =================
# 1. 想要导入的文件名（可选，不带或带 .csv 后缀）
#    如果留空为 None，则导入文件夹下所有 CSV 文件
TARGET_FILE = None  # e.g., "sales" 或 "sales.csv"

# 2. 想要导入的数据库模式 (Schema)
TARGET_SCHEMA = "makeup_consumer_events"

# 3. 数据库连接设置
DB_CONFIG = {
    'host': 'localhost',
    'database': 'postgres',
    'user': 'postgres',
    'password': '',
    'port': 5432
}
# ========================================================

def import_csvs_to_postgres(folder_path, schema, db_params, target_file=None):
    """
    通用导入脚本
    """
    print(f"📁 文件夹路径: {folder_path}")
    print(f"🗂️ 目标模式 (Schema): {schema}")
    if target_file:
        print(f"🎯 目标文件: {target_file}")
    else:
        print("📁 目标: 处理文件夹下所有 .csv 文件")
    
    conn = None
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # 1. 创建模式
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
        conn.commit()
        
        # 2. 扫描文件
        if target_file:
            csv_target = target_file if target_file.endswith('.csv') else target_file + '.csv'
            full_path = os.path.join(folder_path, csv_target)
            if not os.path.exists(full_path):
                print(f"⚠️ 找不到指定文件: {csv_target}")
                return
            csv_files = [csv_target]
        else:
            csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
            
        if not csv_files:
            print("⚠️ 没找到 CSV 文件")
            return
            
        for file in csv_files:
            file_path = os.path.join(folder_path, file)
            table_name = os.path.splitext(file)[0].lower()
            
            # 读取并清理列名
            df = pd.read_csv(file_path)
            df.columns = [str(c).strip().lower().replace(' ', '_').replace('-', '_') for c in df.columns]
            
            # 3. 动态建表 (核心代码行)
            cols = ', '.join([f'"{n}" {"BIGINT" if "int" in str(t) else "DOUBLE PRECISION" if "float" in str(t) else "TEXT"}' for n, t in zip(df.columns, df.dtypes)])
            cursor.execute(f'DROP TABLE IF EXISTS {schema}."{table_name}";')
            cursor.execute(f'CREATE TABLE {schema}."{table_name}" ({cols});')
            
            # 4. 批量搬运 (核心代码行)
            data = [tuple(x) for x in df.where(pd.notnull(df), None).values.tolist()]
            insert_sql = f'INSERT INTO {schema}."{table_name}" VALUES %s'
            execute_values(cursor, insert_sql, data)
            
            conn.commit()
            print(f"✅ 文件 [{file}] 已成功导入至 [{schema}.{table_name}]")
            
    except Exception as e:
        print(f"❌ 运行出错: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    # 获取当前文件夹路径
    current_folder = os.path.dirname(os.path.abspath(__file__)) 

    # 执行导入
    import_csvs_to_postgres(
        folder_path=current_folder, 
        schema=TARGET_SCHEMA, 
        db_params=DB_CONFIG, 
        target_file=TARGET_FILE
    )
