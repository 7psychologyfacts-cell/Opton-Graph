"""
NIFTY/BANKNIFTY Live Option Chain Visualizer
Streamlit App for Upstox API
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import os

# Page configuration
st.set_page_config(
    page_title="Live Option Chain Visualizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #00ff88;
        text-align: center;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #00ff88;
        color: black;
        font-weight: bold;
        border: none;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #00cc6a;
    }
    .metric-box {
        background: rgba(30, 30, 46, 0.8);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00ff88;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

class UpstoxOptionChain:
    """Upstox API handler"""
    
    def __init__(self, access_token):
        self.base_url = "https://api.upstox.com/v2"
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
    
    def test_connection(self):
        """Test API connection"""
        try:
            url = f"{self.base_url}/market-quote/ltp"
            params = {'instrument_key': 'NSE_INDEX|Nifty 50'}
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_option_chain(self, instrument_key, expiry_date):
        """Fetch option chain data"""
        url = f"{self.base_url}/option/chain"
        params = {'instrument_key': instrument_key, 'expiry_date': expiry_date}
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def process_data(self, option_data, num_strikes=20):
        """Process API response"""
        if not option_data or option_data.get('status') != 'success':
            return pd.DataFrame()
        
        rows = []
        for item in option_data['data']:
            strike = item['strike_price']
            spot = item['underlying_spot_price']
            
            # Call data
            if item.get('call_options') and item['call_options'].get('market_data'):
                call = item['call_options']['market_data']
                rows.append({
                    'strike': strike, 'type': 'CE', 'oi': call.get('oi', 0),
                    'ltp': call.get('ltp', 0), 'volume': call.get('volume', 0),
                    'underlying': spot
                })
            
            # Put data
            if item.get('put_options') and item['put_options'].get('market_data'):
                put = item['put_options']['market_data']
                rows.append({
                    'strike': strike, 'type': 'PE', 'oi': put.get('oi', 0),
                    'ltp': put.get('ltp', 0), 'volume': put.get('volume', 0),
                    'underlying': spot
                })
        
        df = pd.DataFrame(rows)
        
        # Filter strikes
        if not df.empty and num_strikes > 0:
            df = self.filter_strikes_around_atm(df, num_strikes)
        
        return df
    
    def filter_strikes_around_atm(self, df, num_strikes):
        """Filter strikes around ATM"""
        if df.empty:
            return df
        
        spot = df['underlying'].iloc[0]
        unique_strikes = sorted(df['strike'].unique())
        atm_strike = min(unique_strikes, key=lambda x: abs(x - spot))
        
        # Find ATM index
        atm_index = unique_strikes.index(atm_strike)
        strikes_each_side = num_strikes // 2
        
        # Get strike range
        start_idx = max(0, atm_index - strikes_each_side)
        end_idx = min(len(unique_strikes), atm_index + strikes_each_side + 1)
        
        # Adjust if near edges
        if start_idx == 0:
            end_idx = min(len(unique_strikes), num_strikes)
        elif end_idx == len(unique_strikes):
            start_idx = max(0, len(unique_strikes) - num_strikes)
        
        filtered_strikes = unique_strikes[start_idx:end_idx]
        return df[df['strike'].isin(filtered_strikes)]

def create_oi_chart(df, instrument, expiry_date):
    """Create OI chart"""
    if df.empty:
        return None, {}
    
    # Prepare data
    ce_df = df[df['type'] == 'CE'].sort_values('strike')
    pe_df = df[df['type'] == 'PE'].sort_values('strike')
    
    # Calculate metrics
    spot_price = df['underlying'].iloc[0]
    atm_strike = min(df['strike'].unique(), key=lambda x: abs(x - spot_price))
    
    total_ce_oi = ce_df['oi'].sum()
    total_pe_oi = pe_df['oi'].sum()
    pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
    
    # Format expiry
    expiry_display = datetime.strptime(expiry_date, '%Y-%m-%d').strftime('%d %b %Y')
    
    # Create figure
    fig = go.Figure()
    
    # Add Call OI bars
    fig.add_trace(go.Bar(
        x=ce_df['strike'], y=ce_df['oi'], name='CALL OI',
        marker_color='#00ff88', width=15,
        hovertemplate='<b>%{x} CE</b><br>OI: %{y:,}<br>LTP: ₹%{customdata:.2f}<extra></extra>',
        customdata=ce_df['ltp']
    ))
    
    # Add Put OI bars
    fig.add_trace(go.Bar(
        x=pe_df['strike'], y=pe_df['oi'], name='PUT OI',
        marker_color='#ff4444', width=15,
        hovertemplate='<b>%{x} PE</b><br>OI: %{y:,}<br>LTP: ₹%{customdata:.2f}<extra></extra>',
        customdata=pe_df['ltp']
    ))
    
    # Add ATM line
    fig.add_vline(
        x=atm_strike, line_dash="dash", line_color="yellow", line_width=3,
        annotation_text=f"ATM: {atm_strike}", annotation_position="top right"
    )
    
    # Update layout
    fig.update_layout(
        title={
            'text': f'<b>{instrument} - OPTION CHAIN OI PROFILE</b><br>'
                   f'<span style="font-size:14px">Expiry: {expiry_display} | '
                   f'Spot: ₹{spot_price:,.2f} | PCR: {pcr:.2f}</span>',
            'x': 0.5, 'xanchor': 'center', 'font': {'size': 20, 'color': 'white'}
        },
        xaxis={
            'title': '<b>STRIKE PRICE</b>', 'tickangle': 45,
            'gridcolor': 'rgba(100, 100, 100, 0.3)'
        },
        yaxis={
            'title': '<b>OPEN INTEREST</b>',
            'gridcolor': 'rgba(100, 100, 100, 0.3)'
        },
        barmode='group', bargap=0.15, template='plotly_dark',
        plot_bgcolor='rgba(0, 0, 0, 0)', paper_bgcolor='rgba(10, 10, 30, 0.9)',
        height=600, hovermode='x unified', showlegend=True
    )
    
    return fig, {
        'spot': spot_price, 'atm': atm_strike, 'pcr': pcr,
        'total_ce': total_ce_oi, 'total_pe': total_pe_oi
    }

def main():
    """Main app function"""
    
    # Header
    st.markdown('<h1 class="main-header">📊 LIVE OPTION CHAIN VISUALIZER</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#aaa;">Real-time NIFTY & BANKNIFTY Data</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ SETTINGS")
        
        # Access Token
        token_input = st.text_input(
            "Upstox Access Token",
            type="password",
            help="Get from https://upstox.com/developer/",
            placeholder="Paste your token here..."
        )
        
        if token_input:
            access_token = token_input
        else:
            # Try from environment
            access_token = os.getenv("eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI0U0JKM0siLCJqdGkiOiI2OTg0MTRhODI5NTgwOTQyZTMwY2NlNTAiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzcwMjYzNzIwLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NzAzMjg4MDB9.2p0nMZ-88xfMwXp8nfMd8ZcXor_hzhBKma3IMlP_POA", "")
        
        # Instrument selection
        st.markdown("---")
        instrument = st.selectbox(
            "Select Instrument",
            ["NIFTY 50", "BANKNIFTY"],
            index=0
        )
        
        instrument_key_map = {
            "NIFTY 50": "NSE_INDEX|Nifty 50",
            "BANKNIFTY": "NSE_INDEX|Nifty Bank"
        }
        selected_key = instrument_key_map[instrument]
        
        # Expiry date
        st.markdown("---")
        st.markdown("### 📅 EXPIRY DATE")
        
        # Generate expiry options
        today = datetime.now()
        expiry_options = []
        for i in range(4):
            days_ahead = 3 - today.weekday() + (i * 7)
            if days_ahead <= 0 and i == 0:
                days_ahead += 7
            expiry_date = today + timedelta(days=days_ahead)
            expiry_options.append(expiry_date.strftime('%Y-%m-%d'))
        
        expiry_type = st.radio("Expiry Type", ["Auto", "Manual"], horizontal=True)
        
        if expiry_type == "Auto":
            expiry_date = st.selectbox("Select Expiry", expiry_options, index=0)
        else:
            manual_date = st.date_input(
                "Enter Date",
                value=datetime.strptime(expiry_options[0], '%Y-%m-%d')
            )
            expiry_date = manual_date.strftime('%Y-%m-%d')
        
        # Number of strikes
        st.markdown("---")
        num_strikes = st.slider(
            "Number of Strikes",
            min_value=10, max_value=50, value=20,
            help="Strikes to show around ATM"
        )
        
        # Refresh
        st.markdown("---")
        auto_refresh = st.checkbox("Auto Refresh", value=False)
        if auto_refresh:
            refresh_time = st.slider("Seconds", 5, 60, 10)
        
        # Fetch button
        st.markdown("---")
        fetch_clicked = st.button("🚀 FETCH LIVE DATA", use_container_width=True)
        
        # Info
        with st.expander("ℹ️ INFO"):
            st.markdown("""
            - **Market Hours**: 9:15 AM - 3:30 PM IST
            - **Token**: Get from Upstox Developer Portal
            - **Expiry**: Usually Thursdays
            """)
    
    # Main content
    if access_token:
        # Initialize
        upstox = UpstoxOptionChain(access_token)
        
        # Test connection
        if fetch_clicked or ('auto_refresh' in locals() and auto_refresh):
            with st.spinner("Checking connection..."):
                if not upstox.test_connection():
                    st.error("❌ Invalid Token")
                    st.stop()
            
            # Fetch data
            with st.spinner(f"Fetching {instrument} data..."):
                option_data = upstox.get_option_chain(selected_key, expiry_date)
                
                if option_data:
                    df = upstox.process_data(option_data, num_strikes)
                    
                    if not df.empty:
                        # Display metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        spot_price = df['underlying'].iloc[0]
                        atm_strike = min(df['strike'].unique(), key=lambda x: abs(x - spot_price))
                        total_ce = df[df['type'] == 'CE']['oi'].sum()
                        total_pe = df[df['type'] == 'PE']['oi'].sum()
                        pcr = total_pe / total_ce if total_ce > 0 else 0
                        
                        with col1:
                            st.metric("Spot Price", f"₹{spot_price:,.2f}")
                        with col2:
                            st.metric("ATM Strike", f"{atm_strike}")
                        with col3:
                            st.metric("PCR", f"{pcr:.2f}")
                        with col4:
                            st.metric("Time", datetime.now().strftime("%H:%M:%S"))
                        
                        # Create chart
                        fig, metrics = create_oi_chart(df, instrument, expiry_date)
                        
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Data table
                            with st.expander("📋 VIEW DATA"):
                                # Format dataframe
                                display_df = df.copy()
                                display_df['oi'] = display_df['oi'].apply(lambda x: f"{x:,}")
                                display_df['ltp'] = display_df['ltp'].apply(lambda x: f"₹{x:,.2f}")
                                
                                st.dataframe(
                                    display_df[['strike', 'type', 'oi', 'ltp', 'volume']],
                                    hide_index=True,
                                    use_container_width=True
                                )
                                
                                # Download
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    "📥 DOWNLOAD CSV",
                                    csv,
                                    f"option_chain_{instrument}_{expiry_date}.csv",
                                    "text/csv",
                                    use_container_width=True
                                )
                            
                            # Analytics
                            with st.expander("📈 ANALYTICS"):
                                tab1, tab2 = st.tabs(["Max OI", "Levels"])
                                
                                with tab1:
                                    max_ce = df[df['type'] == 'CE'].loc[df['oi'].idxmax()]
                                    max_pe = df[df['type'] == 'PE'].loc[df['oi'].idxmax()]
                                    st.write(f"**Max Call OI**: ₹{max_ce['strike']} ({max_ce['oi']:,})")
                                    st.write(f"**Max Put OI**: ₹{max_pe['strike']} ({max_pe['oi']:,})")
                                
                                with tab2:
                                    support = df[df['type'] == 'PE'].nlargest(3, 'oi')['strike'].min()
                                    resistance = df[df['type'] == 'CE'].nlargest(3, 'oi')['strike'].max()
                                    st.write(f"**Support**: ₹{support}")
                                    st.write(f"**Resistance**: ₹{resistance}")
                        else:
                            st.warning("No chart data")
                    else:
                        st.warning("No data available")
                else:
                    st.error("API Error")
            
            # Auto refresh
            if auto_refresh:
                time.sleep(refresh_time)
                st.rerun()
        else:
            # Initial state
            st.info("👈 Configure settings and click 'FETCH LIVE DATA'")
    else:
        st.warning("Please enter Access Token in sidebar")

# Run app
if __name__ == "__main__":
    main()
