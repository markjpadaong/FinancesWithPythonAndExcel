import streamlit as st #interactive web based package
import pandas as pd #data manipulation
import plotly.express as px #data visualization
import json #stores description and categories
import os

#note - to run use: streamlit run main2.py

st.set_page_config(page_title="Finance App", page_icon="💰", layout="wide")

category_file = "categories.json"
expense_file = "categorized_expenses.csv"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": [],
    }
    
if os.path.exists(category_file): #checks if path exists
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)
        
def save_categories(): #write to file, to save categories
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

def categorize_transactions(df):
    df["Category"] = "Uncategorized" #default set all to uncategorized
    df["Expense Type"] = "Personal"
    df["Amount"] = df["Amount"] *-1
    
    for category, keywords in st.session_state.categories.items(): 
        if category == "Uncategorized" or not keywords: #
            continue
        
        lowered_keywords = [keyword.lower().strip() for keyword in keywords] #for optimal comparisons
        for idx, row in df.iterrows(): #loops for matching description and keywords, if saved -> reassigns to given category
            description = row["Description"].lower().strip()
            if any(keyword in description for keyword in lowered_keywords):
                df.at[idx, "Category"] = category 
    return df  

def load_transactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns] #remove trailing,leading white spaces
        #formatting
        #df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        #df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y") 
        
        
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]: #takes new categories associated with words and saves to json
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

def merge_saved_expense_data(current_df):
    if not os.path.exists(expense_file):
        return current_df

    saved_df = pd.read_csv(expense_file)

    if "Transaction Date" in saved_df.columns:
        saved_df["Transaction Date"] = pd.to_datetime(saved_df["Transaction Date"], errors="coerce")
    if "Transaction Date" in current_df.columns:
        current_df["Transaction Date"] = pd.to_datetime(current_df["Transaction Date"], errors="coerce")

    columns_to_merge = ["Transaction Date", "Description", "Category", "Expense Type"]
    saved_df = saved_df[columns_to_merge].drop_duplicates()

    merged = current_df.merge(
        saved_df,
        on=["Transaction Date", "Description"],
        how="left",
        suffixes=("", "_saved")
    )

    if "Category_saved" in merged.columns:
        merged["Category"] = merged["Category_saved"].fillna(merged["Category"])

    if "Expense Type_saved" in merged.columns:
        merged["Expense Type"] = merged["Expense Type_saved"].fillna(merged["Expense Type"])

    merged = merged.drop(columns=[col for col in ["Category_saved", "Expense Type_saved"] if col in merged.columns])

    return merged

def main():
    st.title("Finance Dashboard")
    
    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])
    
    if uploaded_file is not None:
        df = load_transactions(uploaded_file) #load csv file with categories
        
        if df is not None:
            debits_df = df[df["Type"] == "Payment"].copy() #payments added to debit tab;sales added to credit tab
            credits_df = df[df["Type"] == "Sale"].copy() 

            if "credits_df" not in st.session_state:
                st.session_state.credits_df = merge_saved_expense_data(credits_df.copy())
            
            if "debits_df" not in st.session_state:
                st.session_state.debits_df = debits_df.copy()
            
            tab2, tab1 = st.tabs(["Expenses (Credit)", "Payments (Debit)"]) 
            
                
            with tab2: #creates container for credit tab
                new_category = st.text_input("New Category Name")
                add_button = st.button("Add Category")
                
                if add_button and new_category:
                    if new_category not in st.session_state.categories: #creates new categories and refreshes
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()

                if "Expense Type" not in st.session_state.credits_df.columns:
                    st.session_state.credits_df["Expense Type"] = "Personal"

                
                st.subheader("Your Expenses")
                st.session_state.credits_df["Transaction Date"] = pd.to_datetime( #take transaction date column(text) and turn into datetime values
                    st.session_state.credits_df["Transaction Date"],
                    errors="coerce"
                )
                
                edited_df = st.data_editor( #configure for better formatting
                    st.session_state.credits_df[["Transaction Date", "Description", "Amount", "Category","Expense Type"]],
                    column_config={
                        "Transaction Date": st.column_config.DateColumn("Transaction Date", format="MM/DD/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="$%.2f "),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys()) #drop down list for categories;changeable
                        ),
                        "Expense Type": st.column_config.SelectboxColumn(
                            "Expense Type",
                            options=["Personal","Shared","Business"]
                        )
                    },
                    hide_index=True, #hide default row numbers;stretches table width;gives table unique id inside streamlit
                    use_container_width=True,
                    key="category_editor"
                )
                
                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        old_category = st.session_state.credits_df.at[idx, "Category"]
                        new_category = row["Category"]
                        new_expense_type = row["Expense Type"]
                
                        st.session_state.credits_df.at[idx, "Category"] = new_category
                        st.session_state.credits_df.at[idx, "Expense Type"] = new_expense_type
                
                        if new_category != old_category:
                            description = row["Description"].lower().strip()
                            merchant_keyword = description.split()[0]
                
                            add_keyword_to_category(new_category, merchant_keyword)
                
                            matches = st.session_state.credits_df["Description"].str.lower().str.contains(
                                merchant_keyword,
                                na=False
                            )
                            st.session_state.credits_df.loc[matches, "Category"] = new_category
                
                    st.session_state.credits_df.to_csv(expense_file, index=False)
                    st.success("Changes saved")
                    st.rerun()
                        
                st.subheader('Expense Summary')
                category_totals = st.session_state.credits_df.groupby(["Expense Type", "Category"])["Amount"].sum().reset_index() #grouped list of categories by amount
                category_totals = category_totals.sort_values(["Expense Type", "Amount"], ascending=[True,False])
                
                st.dataframe(
                    category_totals, 
                    column_config={
                     "Amount": st.column_config.NumberColumn("Amount", format="$%.2f")   
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                fig = px.pie(
                    category_totals,
                    values="Amount",
                    names="Category",
                    title="Expenses by Category"
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab1: #creates container for debit tab
                st.subheader("Payments Summary")
                total_payments = debits_df["Amount"].sum()
                st.metric("Total Payments", f"${total_payments:,.2f} ")

                st.session_state.debits_df["Transaction Date"] = pd.to_datetime(
                    st.session_state.debits_df["Transaction Date"],
                    errors="coerce"
                )
                
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Transaction Date", "Amount"]],
                    column_config={
                        "Transaction Date": st.column_config.DateColumn("Transaction Date", format="MM/DD/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="$%.2f "),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="debits_editor"
                )
                    

               
        
main()