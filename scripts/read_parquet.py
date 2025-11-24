#!/usr/bin/env python3
"""
Simple script to read and display parquet files from the data collection.

Usage:
    python scripts/read_parquet.py [file_path]
    
If no file path is provided, it will use the most recent parquet file in data/raw/
"""

import sys
from pathlib import Path

import pandas as pd


def read_parquet_file(file_path: Path | None = None):
    """
    Read and display a parquet file.
    
    Args:
        file_path: Path to parquet file. If None, uses most recent in data/raw/
    """
    if file_path is None:
        # Find the most recent parquet file
        data_dir = Path("data/raw")
        if not data_dir.exists():
            print(f"Error: {data_dir} does not exist")
            return
        
        parquet_files = list(data_dir.glob("*.parquet"))
        if not parquet_files:
            print(f"Error: No parquet files found in {data_dir}")
            return
        
        file_path = max(parquet_files, key=lambda p: p.stat().st_mtime)
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return
    
    print(f"Reading: {file_path}\n")
    
    # Read the parquet file
    df = pd.read_parquet(file_path)
    
    print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n")
    print("Columns:", list(df.columns))
    print("\n" + "=" * 80)
    print("First few rows:")
    print("=" * 80)
    print(df.head(10).to_string())
    
    if "market_price" in df.columns:
        print("\n" + "=" * 80)
        print("Price Statistics:")
        print("=" * 80)
        print(df["market_price"].describe())
        
        print("\n" + "=" * 80)
        print("Cards by Category:")
        print("=" * 80)
        if "category" in df.columns:
            print(df.groupby("category")["market_price"].agg(["count", "mean", "min", "max"]).round(2))
        
        print("\n" + "=" * 80)
        print("Top Cards by Price:")
        print("=" * 80)
        if "card_name" in df.columns:
            top_cards = df.groupby("card_name")["market_price"].mean().sort_values(ascending=False)
            print(top_cards.head(10).to_string())


def main():
    """Main entry point."""
    file_path = None
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
    
    read_parquet_file(file_path)


if __name__ == "__main__":
    main()

