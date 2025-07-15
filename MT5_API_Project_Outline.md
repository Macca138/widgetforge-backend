# MT5 API Access Project Outline
## Request for Read-Only Account Data API - 5ers Prop Firm

---

## Executive Summary

We are requesting the development of a secure, read-only API that allows authorized access to basic account information for our prop trading accounts. This API will enable us to create customizable widgets displaying account metrics (balance, equity, open positions, P/L) for live streaming and internal monitoring purposes.

**Key Points:**
- **Read-only access only** - No trading or account modification capabilities
- **Investor password authentication** - Using existing investor-level credentials
- **Private, internal use** - No public-facing access or data exposure
- **Legitimate business purpose** - Enhanced streaming content and account monitoring

---

## Project Overview

### Background
Our company operates a live streaming platform on EVMUX where we showcase trading activities and educational content. We currently have a working system that displays market data and basic MT5 information through our WidgetForge Backend application.

### Objective
Create customizable HTML widgets that display real-time account information including:
- Account balance
- Account equity
- Open trades/positions
- Current profit/loss on positions
- Basic account statistics

### Current Technical Infrastructure
- **Backend**: Python FastAPI application hosted on Windows Server 2019 VPS
- **Frontend**: HTML/JavaScript widgets with real-time updates
- **Security**: HTTPS with API key authentication
- **Existing MT5 Integration**: Local terminal polling system

---

## Technical Requirements

### API Specifications Needed

#### Authentication
- **Method**: API key-based authentication
- **Account Access**: Via investor passwords (read-only credentials)
- **Rate Limiting**: Reasonable limits to prevent abuse
- **IP Restrictions**: Whitelist our server IP addresses

#### Required Endpoints
1. **Account Information**
   - GET `/api/account/{account_id}/info`
   - Returns: balance, equity, margin, free margin, currency

2. **Position Data**
   - GET `/api/account/{account_id}/positions`
   - Returns: open positions, symbols, volume, profit/loss, open time

3. **Account Summary**
   - GET `/api/account/{account_id}/summary`
   - Returns: consolidated account metrics

#### Data Format
- **Response Format**: JSON
- **Update Frequency**: Real-time or near real-time (5-second intervals acceptable)
- **Data Retention**: Current positions only (no historical data required)

#### Security Requirements
- **HTTPS Only**: All API communications encrypted
- **API Key Management**: Secure key generation and rotation capability
- **Access Logging**: Audit trail of all API requests
- **Error Handling**: Proper error responses without exposing sensitive information

---

## Security & Access Controls

### Data Access Limitations
- **Read-Only**: No ability to place trades, modify positions, or change account settings
- **Investor Level**: Using investor passwords which inherently limit access
- **Specific Accounts**: Only accounts we own/manage with proper authorization
- **No Sensitive Data**: No access to personal information, passwords, or financial details beyond basic account metrics

### Network Security
- **IP Whitelisting**: Restrict API access to our server IP addresses
- **Rate Limiting**: Prevent abuse through reasonable request limits
- **SSL/TLS**: All communications encrypted in transit
- **API Key Rotation**: Regular key rotation capability

### Data Handling
- **No Storage**: Account data not permanently stored on our systems
- **Cache Only**: Temporary caching for widget display (5-minute TTL)
- **No Third-Party Sharing**: Data used exclusively for our internal widgets
- **GDPR Compliance**: No personal data processing or storage

---

## Implementation Plan

### Phase 1: API Development (5ers Responsibility)
- Create secure API endpoints
- Implement authentication system
- Set up monitoring and logging
- Provide API documentation

### Phase 2: Integration (Our Responsibility)
- Integrate API calls into existing WidgetForge Backend
- Develop admin panel for account management
- Create customizable widget templates
- Implement real-time data streaming

### Phase 3: Testing & Deployment
- Security testing and validation
- Performance optimization
- Production deployment
- Monitoring and maintenance

---

## What We Need from 5ers

### Technical Requirements
1. **API Development**
   - Secure REST API with the endpoints specified above
   - Authentication system using API keys
   - Rate limiting and security controls
   - Comprehensive API documentation

2. **Access Management**
   - Method to register our API keys
   - IP whitelisting capability
   - Account linking (map investor passwords to API access)

3. **Support & Maintenance**
   - Technical documentation
   - Contact person for technical issues
   - Notification of any API changes or maintenance

### Security Considerations
- Audit our proposed implementation
- Review and approve our security measures
- Establish monitoring protocols
- Define incident response procedures

---

## Data Usage & Privacy

### Intended Use Cases
1. **Live Streaming Widgets**: Display account metrics during live trading sessions
2. **Internal Monitoring**: Track account performance across multiple accounts
3. **Educational Content**: Show real trading results without exposing sensitive information

### Data Protection Measures
- **Minimal Data**: Only essential account metrics accessed
- **Temporary Storage**: Data cached briefly for display purposes only
- **Access Controls**: Restricted to authorized personnel only
- **No Public Access**: Widgets displayed only on our controlled platforms

### Compliance
- **No Personal Data**: No access to trader personal information
- **Financial Data**: Only basic account metrics (balance, equity, P/L)
- **Regulatory Compliance**: Adherence to all applicable financial regulations
- **Data Retention**: No long-term storage of account data

---

## Benefits for 5ers

### Enhanced Trader Experience
- Professional-looking account displays
- Real-time performance monitoring
- Increased engagement through live streaming

### Technical Benefits
- Controlled, secure access to account data
- Reduced load on MT5 terminals
- Centralized API management

### Business Benefits
- Support for trader marketing and education
- Professional presentation of trading results
- Competitive advantage through advanced features

---

## Risk Mitigation

### Technical Risks
- **API Security**: Comprehensive security measures and regular audits
- **Data Breach**: Minimal data exposure due to read-only, basic metrics only
- **System Overload**: Rate limiting and proper error handling

### Business Risks
- **Misuse**: Clear usage agreements and monitoring
- **Compliance**: Regular review of regulatory requirements
- **Reputation**: Professional implementation and responsible data handling

---

## Example Implementation

To demonstrate our commitment to responsible API usage, we've prepared an example of how we would implement the API client. This script showcases all the safety measures and best practices we would employ:

### Key Safety Features of Our Implementation

1. **Strict Rate Limiting**: Maximum 1 request per account per 5 seconds
2. **Read-Only Operations**: Only GET requests allowed, no trading capabilities
3. **Fault Tolerance**: 5-second timeouts and automatic retry logic
4. **Comprehensive Logging**: Full audit trail without exposing sensitive data
5. **Minimal Server Load**: Efficient caching and targeted data requests

### Sample API Client Code

```python
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
import logging
from functools import wraps
import hashlib

# Configuration
API_ENDPOINT = "https://api.the5ers.com/mt5/investor"  # Example endpoint
API_KEY = "your_api_key_here"
MAX_REQUESTS_PER_SECOND = 0.2  # Max 1 request per 5 seconds per account
CONNECTION_TIMEOUT = 5  # 5 second timeout
MAX_RETRIES = 3

# Set up logging to show all operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Ensures we never exceed rate limits"""
    def __init__(self, min_interval_seconds: float):
        self.min_interval = min_interval_seconds
        self.last_request_time = {}
    
    def wait_if_needed(self, account_id: str):
        """Wait if necessary to respect rate limit"""
        current_time = time.time()
        
        if account_id in self.last_request_time:
            elapsed = current_time - self.last_request_time[account_id]
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.info(f"Rate limiting: waiting {sleep_time:.2f}s for account {account_id}")
                time.sleep(sleep_time)
        
        self.last_request_time[account_id] = time.time()

class SafeMT5BrokerAPI:
    """
    Safe, read-only API client for The 5ers MT5 data
    
    Features:
    - Strict rate limiting (max 1 request per 5 seconds per account)
    - Connection timeouts to prevent hanging
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    - Read-only operations only
    - Full audit logging
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(min_interval_seconds=5.0)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'EVMUX-Widget-Reader/1.0',
            'Accept': 'application/json'
        })
        
    def _make_safe_request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """
        Make a safe HTTP request with all protections
        
        - Read-only (GET requests only)
        - Timeout protection
        - Retry logic
        - Error handling
        """
        if method != "GET":
            raise ValueError("Only GET requests allowed for read-only access")
        
        kwargs['timeout'] = CONNECTION_TIMEOUT
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.request(method, url, **kwargs)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    logger.warning(f"Rate limited by server, waiting {2**attempt}s")
                    time.sleep(2 ** attempt)
                elif response.status_code == 401:
                    logger.error("Authentication failed - check API key")
                    return None
                else:
                    logger.error(f"Request failed: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{MAX_RETRIES})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error (attempt {attempt + 1}/{MAX_RETRIES})")
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                
        return None
    
    def get_account_data(self, account_number: str, investor_password: str) -> Optional[Dict]:
        """
        Get account data using investor password (read-only)
        
        This is the ONLY method that contacts the broker's server
        """
        # Rate limit per account
        self.rate_limiter.wait_if_needed(account_number)
        
        # Hash password for secure transmission (if required by API)
        password_hash = hashlib.sha256(investor_password.encode()).hexdigest()
        
        # Log the request (but never log passwords)
        logger.info(f"Requesting data for account {account_number}")
        
        # Make the API call
        url = f"{API_ENDPOINT}/account/{account_number}"
        params = {
            'investor_password_hash': password_hash,
            'fields': 'balance,equity,margin,positions'  # Only request what we need
        }
        
        start_time = time.time()
        data = self._make_safe_request("GET", url, params=params)
        request_time = time.time() - start_time
        
        if data:
            logger.info(f"Successfully retrieved data for {account_number} in {request_time:.2f}s")
            # Add timestamp for caching
            data['timestamp'] = datetime.utcnow().isoformat()
        else:
            logger.error(f"Failed to retrieve data for {account_number}")
            
        return data

    def get_multiple_accounts(self, accounts: List[Dict[str, str]]) -> Dict[str, Dict]:
        """
        Get data for multiple accounts with rate limiting
        
        accounts: List of {'account_number': '...', 'investor_password': '...'}
        """
        results = {}
        
        for account_info in accounts:
            account_number = account_info['account_number']
            investor_password = account_info['investor_password']
            
            # Get data with all safety measures
            data = self.get_account_data(account_number, investor_password)
            
            if data:
                results[account_number] = data
            else:
                results[account_number] = {
                    'error': 'Failed to retrieve data',
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        return results

# Example usage showing safety measures
def example_safe_usage():
    """
    Demonstration of safe API usage that won't impact broker's servers
    """
    # Initialize API client
    api = SafeMT5BrokerAPI(api_key=API_KEY)
    
    # Example accounts (in production, these come from your database)
    accounts_to_monitor = [
        {'account_number': '50012345', 'investor_password': 'investor_pass_1'},
        {'account_number': '50023456', 'investor_password': 'investor_pass_2'},
    ]
    
    # Continuous monitoring with all protections
    while True:
        logger.info("Starting account update cycle")
        
        try:
            # Get all account data (automatically rate limited)
            account_data = api.get_multiple_accounts(accounts_to_monitor)
            
            # Process the data (send to your widgets)
            for account, data in account_data.items():
                if 'error' not in data:
                    logger.info(f"Account {account}: Balance=${data.get('balance', 0):.2f}")
                    # Send to your WebSocket/widget system here
                    
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {str(e)}")
            time.sleep(30)  # Wait before retrying
            
        # Wait before next update cycle
        time.sleep(10)  # Additional delay between full cycles
```

### Implementation Safeguards

This implementation includes several key safeguards that protect your servers:

1. **Rate Limiting**: Built-in rate limiter ensures no more than 1 request per 5 seconds per account
2. **Connection Timeouts**: 5-second timeout prevents hanging connections
3. **Exponential Backoff**: Automatic retry with increasing delays
4. **Error Handling**: Graceful handling of all error conditions
5. **Audit Logging**: Complete audit trail of all operations
6. **Read-Only**: Code structure prevents any non-GET operations
7. **Minimal Requests**: Only requests essential data fields

This approach is identical to what established services like MyFXBook, FXBlue, and other account monitoring platforms use for broker integrations.

---

## Conclusion

This is a straightforward request for read-only account data to enhance our YouTube live streaming experience. By displaying real account metrics during live trading sessions, we can provide viewers with authentic, transparent content that showcases actual trading results from 5ers traders.

The read-only nature of the API and limited scope of data access minimize any technical risks while supporting our mutual goal of attracting more traders to the 5ers platform through engaging, educational content.

---

## Contact Information

For technical questions or clarifications regarding this project outline, please contact:

**Project Lead**: [Your Name]  
**Company**: [Your Company]  
**Email**: [Your Email]  
**Technical Contact**: [Technical Lead if different]

---

*This document is confidential and intended solely for 5ers Prop Firm's review in connection with the proposed MT5 API access project.*