import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Database Viewer", page_icon="🗄️")
st.title("Database Viewer - MoSPI Data")

# Database path
DB_PATH = "data/mospi.db"

def get_table_data(table_name: str):
    """Fetch data from a specific table"""
    try:
        conn = sqlite3.connect(DB_PATH)
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error reading {table_name}: {str(e)}")
        return pd.DataFrame()

def format_table_data(df: pd.DataFrame, table_name: str):
    """Format and display table data"""
    if df.empty:
        st.info(f"No data in {table_name} table")
        return
    
    st.subheader(f"{table_name.title()} Table")
    st.write(f"**Total rows:** {len(df)}")
    
    # Display the dataframe
    st.dataframe(df, use_container_width=True)
    
    # Show sample data if table is large
    if len(df) > 10:
        st.write("**Sample data (first 10 rows):**")
        st.dataframe(df.head(10), use_container_width=True)

def main():
    if not os.path.exists(DB_PATH):
        st.error("Database not found. Please run the scraper first to create the database.")
        return
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Table to View",
        ["Overview", "documents", "files", "tables"]
    )
    
    if page == "Overview":
        st.header("Database Overview")
        
        # Get table counts
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            st.write("**Available Tables:**")
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                st.write(f"- **{table_name}**: {count} rows")
            
            conn.close()
            
            st.write("---")
            st.write("**Database Location:**", DB_PATH)
            st.write("**Last Updated:**", datetime.fromtimestamp(os.path.getmtime(DB_PATH)).strftime("%Y-%m-%d %H:%M:%S"))
            
        except Exception as e:
            st.error(f"Error reading database overview: {str(e)}")
    
    elif page == "documents":
        st.header("Documents Table")
        df = get_table_data("documents")
        format_table_data(df, "documents")
        
        # Show some statistics
        if not df.empty:
            st.write("---")
            st.write("**Statistics:**")
            if 'date_published' in df.columns:
                st.write(f"- Date range: {df['date_published'].min()} to {df['date_published'].max()}")
            if 'category' in df.columns:
                st.write(f"- Categories: {', '.join(df['category'].unique())}")
    
    elif page == "files":
        st.header("Files Table")
        df = get_table_data("files")
        format_table_data(df, "files")
        
        # Show some statistics
        if not df.empty:
            st.write("---")
            st.write("**Statistics:**")
            if 'downloaded' in df.columns:
                downloaded = df['downloaded'].sum()
                total = len(df)
                st.write(f"- Downloaded: {downloaded}/{total} ({downloaded/total*100:.1f}%)")
            if 'processed' in df.columns:
                processed = df['processed'].sum()
                st.write(f"- Processed: {processed}/{total} ({processed/total*100:.1f}%)")
    
    elif page == "tables":
        st.header("Extracted Tables")
        df = get_table_data("tables")
        format_table_data(df, "tables")
        
        # Show table details
        if not df.empty:
            st.write("---")
            st.write("**Table Details:**")
            
            # Show sample table content
            for idx, row in df.head(5).iterrows():
                st.write(f"**Table {idx + 1}:** {row['n_rows']} rows × {row['n_cols']} columns")
                if 'table_json' in row and row['table_json']:
                    try:
                        import json
                        table_data = json.loads(row['table_json'])
                        if table_data:
                            table_df = pd.DataFrame(table_data)
                            st.dataframe(table_df, use_container_width=True)
                    except:
                        st.write("Could not parse table data")
                st.write("---")
    
    # Download option
    st.sidebar.write("---")
    if st.sidebar.button("Download All Data"):
        try:
            conn = sqlite3.connect(DB_PATH)
            
            # Create Excel file with all tables
            with pd.ExcelWriter('mospi_database_export.xlsx', engine='openpyxl') as writer:
                for table_name in ['documents', 'files', 'tables']:
                    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                    df.to_excel(writer, sheet_name=table_name, index=False)
            
            conn.close()
            
            # Read the file and provide download
            with open('mospi_database_export.xlsx', 'rb') as f:
                st.sidebar.download_button(
                    label="Download Excel File",
                    data=f.read(),
                    file_name="mospi_database_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            # Clean up
            os.remove('mospi_database_export.xlsx')
            
        except Exception as e:
            st.sidebar.error(f"Error creating export: {str(e)}")

if __name__ == "__main__":
    main()
