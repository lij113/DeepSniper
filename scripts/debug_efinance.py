import sys
import os
import pandas as pd
import efinance as ef

# 添加项目路径
sys.path.append("/root/my_workspace/DeepSniper")

def main():
    codes = ["600519", "300750", "000858", "601318", "600036", "000001"]
    print(f"🔍 正在测试拉取 {len(codes)} 只股票: {codes}")
    
    try:
        # 直接调用底层接口，不经过 data_fetch 清洗
        df = ef.stock.get_quote_snapshot(codes)
        
        print("\n-------- 返回数据类型 --------")
        print(type(df))
        
        if df is None:
            print("❌ 返回为 None (通常是网络问题或被封IP)")
            return

        if isinstance(df, pd.DataFrame):
            print("\n-------- 列名检查 --------")
            print(df.columns.tolist())
            
            print("\n-------- 前3行原始数据 --------")
            print(df.head(3))
            
            # 检查清洗逻辑是否误杀
            print("\n-------- 检查清洗逻辑 --------")
            if '代码' in df.columns and '最新价' in df.columns:
                print("✅ 关键列 '代码' 和 '最新价' 存在")
                clean_df = df.dropna(subset=['代码', '最新价'])
                print(f"清洗前行数: {len(df)}, 清洗后行数: {len(clean_df)}")
            else:
                print("❌ 缺少关键列！这会导致 data_fetch 返回空！")
        else:
            print("\n-------- 非 DataFrame 返回 --------")
            print(df)

    except Exception as e:
        print(f"\n❌ 发生异常: {e}")

if __name__ == "__main__":
    main()