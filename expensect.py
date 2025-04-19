import streamlit as st
import re
from datetime import datetime
import pandas as pd

# Set page configuration and custom CSS
st.set_page_config(page_title="Expense Splitter", page_icon="💰", layout="wide")

# Custom CSS for styling
def load_css():
    st.markdown("""
    <style>
    /* Main container styling */
    .main {
        background-color: #f8f9fa;
        padding: 10px;
    }
    
    /* Header styling */
    h1 {
        color: #4b6584;
        text-align: center;
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #20bf6b;
    }
    
    h2, h3 {
        color: #4b6584;
        margin-top: 1rem;
    }
    
    /* Card styling for different sections */
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #20bf6b;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    
    .stButton>button:hover {
        background-color: #0ea55a;
    }
    
    /* Input field styling */
    .stTextInput>div>div>input {
        border-radius: 5px;
        border: 1px solid #dfe4ea;
    }
    
    /* Table styling */
    .dataframe {
        width: 100%;
        border-collapse: collapse;
    }
    
    .dataframe th {
        background-color: #4b6584;
        color: white;
        padding: 8px;
        text-align: left;
    }
    
    .dataframe td {
        padding: 8px;
        border-bottom: 1px solid #dfe4ea;
    }
    
    .dataframe tr:nth-child(even) {
        background-color: #f1f2f6;
    }
    
    /* Transaction cards */
    .transaction-card {
        background-color: #f1f2f6;
        border-left: 4px solid #20bf6b;
        padding: 10px 15px;
        margin-bottom: 10px;
        border-radius: 5px;
    }
    
    .transaction-amount {
        font-weight: bold;
        color: #20bf6b;
    }
    
    /* Response area */
    .response-area {
        background-color: #e3f9ee;
        border-left: 4px solid #20bf6b;
        padding: 15px;
        border-radius: 5px;
        margin-top: 15px;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #f1f2f6;
        border-radius: 5px;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #dfe4ea;
        color: #a5b1c2;
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

class ExpenseSplitter:
    def _init_(self):
        # Initialize or load existing expenses
        if 'expenses' not in st.session_state:
            st.session_state.expenses = []
        if 'people' not in st.session_state:
            st.session_state.people = set()
        
    def add_expense(self, paid_by, amount, description, split_among=None, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if split_among is None:
            split_among = list(st.session_state.people)
        else:
            # Add all people to the global set
            for person in split_among:
                st.session_state.people.add(person)
        
        # Add payer to the global set of people
        st.session_state.people.add(paid_by)
        
        # Calculate the amount per person
        amount_per_person = amount / len(split_among)
        
        # Add the expense to the list
        st.session_state.expenses.append({
            "date": date,
            "paid_by": paid_by,
            "amount": amount,
            "description": description,
            "split_among": split_among,
            "amount_per_person": amount_per_person
        })
        
        return f"Added expense: {description} - ${amount:.2f} paid by {paid_by}, split among {', '.join(split_among)}."
    
    def calculate_balances(self):
        # Initialize balance dict
        balances = {person: 0 for person in st.session_state.people}
        
        # Calculate what each person has paid and owes
        for expense in st.session_state.expenses:
            paid_by = expense["paid_by"]
            amount = expense["amount"]
            split_among = expense["split_among"]
            amount_per_person = expense["amount_per_person"]
            
            # Add amount to the balance of the person who paid
            balances[paid_by] += amount
            
            # Subtract amount from the balance of each person who shares the expense
            for person in split_among:
                balances[person] -= amount_per_person
        
        return balances
    
    def get_transactions(self):
        balances = self.calculate_balances()
        
        # Separate debtors and creditors
        debtors = {person: balance for person, balance in balances.items() if balance < 0}
        creditors = {person: balance for person, balance in balances.items() if balance > 0}
        
        transactions = []
        
        # Create transaction list
        for debtor, debt in sorted(debtors.items(), key=lambda x: x[1]):
            debt = abs(debt)  # Make the debt positive for calculations
            for creditor, credit in sorted(creditors.items(), key=lambda x: x[1], reverse=True):
                if debt <= 0 or credit <= 0:
                    continue
                    
                amount = min(debt, credit)
                transactions.append({
                    "from": debtor,
                    "to": creditor,
                    "amount": amount
                })
                
                # Update remaining balances
                debt -= amount
                creditors[creditor] -= amount
                
        return transactions
    
    def parse_command(self, command):
        # Convert command to lowercase
        command = command.lower()
        
        # Check for expense command patterns
        expense_pattern = r'(?P<paid_by>\w+)\s+paid\s+(?P<amount>\d+(\.\d+)?)\s+for\s+(?P<description>.+?)((\s+split\s+(?:between|among|with)\s+(?P<split_among>.+?))?(\s+on\s+(?P<date>.+))?)?$'
        match = re.search(expense_pattern, command)
        
        if match:
            paid_by = match.group('paid_by').strip()
            amount = float(match.group('amount'))
            description = match.group('description').strip()
            
            split_among_str = match.group('split_among')
            date_str = match.group('date')
            
            # Parse the people to split among
            split_among = None
            if split_among_str:
                split_among = [person.strip() for person in re.split(r',\s*|(?:\s+and\s+)', split_among_str)]
                # Include the payer if they're not already in the list
                if paid_by not in split_among:
                    split_among.append(paid_by)
            
            # Parse the date if provided
            date = None
            if date_str:
                try:
                    date = datetime.strptime(date_str.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
                except ValueError:
                    date = datetime.now().strftime("%Y-%m-%d")
            
            return self.add_expense(paid_by, amount, description, split_among, date)
        
        # Check for balance command
        if "balance" in command or "who owes" in command or "owes who" in command:
            balances = self.calculate_balances()
            transactions = self.get_transactions()
            
            if not transactions:
                return "All settled up! No one owes anything."
            
            result = "Here's who owes whom:\n"
            for t in transactions:
                result += f"{t['from']} owes {t['to']} ${t['amount']:.2f}\n"
            
            return result
        
        # Check for summary command
        if "summary" in command or "list expenses" in command:
            if not st.session_state.expenses:
                return "No expenses recorded yet."
            
            result = "Expense Summary:\n"
            for idx, expense in enumerate(st.session_state.expenses):
                result += f"{idx+1}. {expense['description']} - ${expense['amount']:.2f} paid by {expense['paid_by']}, " \
                         f"split among {', '.join(expense['split_among'])}\n"
            
            return result
        
        # Check for help command
        if "help" in command:
            return """
            I understand these commands:
            - "[name] paid [amount] for [description] split among/between/with [person1, person2, ...]"
            - "balance" or "who owes" to see who owes whom
            - "summary" or "list expenses" to see all recorded expenses
            - "help" to see this message
            - "clear" to reset all expenses
            """
        
        # Check for clear command
        if "clear" in command or "reset" in command:
            st.session_state.expenses = []
            st.session_state.people = set()
            return "All expenses have been cleared."
        
        return "I didn't understand that command. Type 'help' to see what I can do."

# Streamlit app
def main():
    # Load custom CSS
    load_css()
    
    # App header
    st.markdown("<h1>💰 Expense Splitter App</h1>", unsafe_allow_html=True)
    
    # Initialize the splitter
    splitter = ExpenseSplitter()
    
    # Two-column layout
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Input section
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Add New Expense")
        
        # Chat input area with examples
        user_input = st.text_input("Enter your expense or command:", 
                                  placeholder="e.g. 'John paid 50 for dinner split among John, Mary, Bob'")
        
        if st.button("Submit"):
            if user_input:
                response = splitter.parse_command(user_input)
                st.session_state.last_response = response
                st.session_state.show_response = True
        
        # Show example commands
        st.markdown("""
        <b>Example commands:</b>
        <ul>
          <li>"John paid 50 for dinner split among John, Mary, Bob"</li>
          <li>"Sarah paid 30 for movie tickets split between Sarah and Mike"</li>
          <li>"balance" or "who owes whom"</li>
          <li>"summary" or "list expenses"</li>
          <li>"clear" to reset all data</li>
        </ul>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Display response if available
        if 'show_response' in st.session_state and st.session_state.show_response:
            st.markdown("<div class='response-area'>", unsafe_allow_html=True)
            st.write(st.session_state.last_response)
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button("Clear Response"):
                st.session_state.show_response = False
        
        # Display expense history
        if st.session_state.expenses:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Expense History")
            expense_data = []
            for expense in st.session_state.expenses:
                expense_data.append([
                    expense["date"],
                    expense["description"],
                    f"${expense['amount']:.2f}",
                    expense["paid_by"],
                    ", ".join(expense["split_among"])
                ])
            
            st.dataframe(pd.DataFrame(
                expense_data,
                columns=["Date", "Description", "Amount", "Paid By", "Split Among"]
            ), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        # Balances and Transactions Section
        if st.session_state.expenses:
            # Current Balances
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Current Balances")
            balances = splitter.calculate_balances()
            
            balance_data = []
            for person, balance in balances.items():
                status = "✅ Settled" if abs(balance) < 0.01 else "💰 Owed money" if balance > 0 else "🔴 Owes money"
                balance_data.append([person, f"${balance:.2f}", status])
            
            st.dataframe(pd.DataFrame(
                balance_data, 
                columns=["Person", "Balance", "Status"]
            ), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Suggested Transactions
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Suggested Transactions")
            transactions = splitter.get_transactions()
            
            if transactions:
                for t in transactions:
                    st.markdown(f"""
                    <div class='transaction-card'>
                      <b>{t['from']}</b> owes <b>{t['to']}</b> <span class='transaction-amount'>${t['amount']:.2f}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("All settled up! No one owes anything.")
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Clear data button
            if st.button("Clear All Expenses"):
                st.session_state.expenses = []
                st.session_state.people = set()
                st.session_state.show_response = True
                st.session_state.last_response = "All expenses have been cleared."
                st.experimental_rerun()
        else:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.info("No expenses added yet. Add an expense to see balances and transaction details.")
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Footer
    st.markdown("<div class='footer'>Expense Splitter App • Made with Streamlit</div>", unsafe_allow_html=True)

if __name__ == "_main_":
    main()