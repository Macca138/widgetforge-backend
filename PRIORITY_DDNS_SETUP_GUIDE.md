# Priority DDNS Setup Guide for EVMUX Integration

## 🚀 Quick Setup Overview (30 minutes total)

1. **Register DDNS Domain** (5 minutes)
2. **Install DDNS Client** (5 minutes) 
3. **Configure Windows Firewall** (5 minutes)
4. **Set up SSL Certificate** (10 minutes)
5. **Test EVMUX Integration** (5 minutes)

---

## Step 1: Register Free DDNS Domain (5 minutes)

### Option A: No-IP.com (Recommended for EVMUX)

1. Go to **https://www.noip.com**
2. Click **Sign Up** → Choose **Free** plan
3. Create account with your email
4. **Verify email** (check spam folder)
5. Login to No-IP dashboard
6. Click **Dynamic DNS** → **Create Hostname**
7. Choose your hostname: `yourcompany.ddns.net`
8. Set **IP Address** to your current public IP (will auto-detect)
9. Click **Create Hostname**

### Alternative: DuckDNS.org (Simpler setup)

1. Go to **https://www.duckdns.org**
2. Login with Google/GitHub
3. Create subdomain: `yourcompany.duckdns.org`
4. Note your **token** (you'll need this)

---

## Step 2: Install DDNS Client on Windows Server (5 minutes)

### For No-IP:

1. **Download No-IP DUC**:
   ```
   https://www.noip.com/download?page=win
   ```

2. **Install Steps**:
   - Run installer as Administrator
   - Enter your No-IP username/password
   - Select your hostname from the list
   - Check **"Run as Windows Service"**
   - Click **Save**

3. **Verify Installation**:
   - Check System Tray for No-IP icon
   - Right-click → **Show** to see status
   - Should show "Good" status

### For DuckDNS (PowerShell method):

1. **Create Update Script**:
   ```powershell
   # Create C:\DuckDNS folder
   New-Item -ItemType Directory -Path "C:\DuckDNS" -Force
   
   # Create update script
   @"
   $domain = "yourcompany"
   $token = "your-token-here"
   Invoke-WebRequest -Uri "https://www.duckdns.org/update?domains=$domain&token=$token&ip=" -UseBasicParsing
   "@ | Out-File -FilePath "C:\DuckDNS\update.ps1"
   ```

2. **Schedule Task**:
   - Open **Task Scheduler**
   - Create Basic Task → Name: "DuckDNS Update"
   - Trigger: Daily, repeat every 5 minutes
   - Action: Start Program
   - Program: `powershell.exe`
   - Arguments: `-File "C:\DuckDNS\update.ps1"`

---

## Step 3: Configure Windows Firewall (5 minutes)

```powershell
# Run PowerShell as Administrator

# Allow inbound HTTP (port 8000)
New-NetFirewallRule -DisplayName "WidgetForge HTTP" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow

# Allow inbound HTTPS (port 443) - for later SSL setup
New-NetFirewallRule -DisplayName "WidgetForge HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow

# Check if rules were created
Get-NetFirewallRule -DisplayName "*WidgetForge*"
```

**Router Configuration** (if behind NAT):
1. Access router admin panel (usually 192.168.1.1)
2. Find **Port Forwarding** section
3. Add rule:
   - **Service Name**: WidgetForge
   - **External Port**: 8000
   - **Internal IP**: [Your server's local IP]
   - **Internal Port**: 8000
   - **Protocol**: TCP

---

## Step 4: Set Up SSL Certificate (10 minutes)

### Method A: Using win-acme (Automated Let's Encrypt)

1. **Download win-acme**:
   ```powershell
   # Create tools directory
   New-Item -ItemType Directory -Path "C:\tools" -Force
   
   # Download win-acme
   Invoke-WebRequest -Uri "https://github.com/win-acme/win-acme/releases/download/v2.2.5.1541/win-acme.v2.2.5.1541.x64.pluggable.zip" -OutFile "C:\tools\win-acme.zip"
   
   # Extract
   Expand-Archive -Path "C:\tools\win-acme.zip" -DestinationPath "C:\tools\win-acme"
   ```

2. **Run Certificate Wizard**:
   ```powershell
   cd C:\tools\win-acme
   .\wacs.exe
   ```

3. **Follow Prompts**:
   - Choose **N** (New certificate)
   - Choose **4** (Manual input)
   - Enter your DDNS domain: `yourcompany.ddns.net`
   - Choose **2** (Http validation)
   - Choose **5** (No additional store)
   - Choose **3** (No additional installation)
   - Confirm settings

4. **Verify Certificate**:
   - Certificate files saved to: `C:\ProgramData\win-acme\httpsacme-v02.api.letsencrypt.org`
   - Auto-renewal scheduled in Task Scheduler

### Method B: Manual Setup with IIS (if using IIS)

1. **Install IIS and SSL** (if not already done):
   ```powershell
   Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole
   Enable-WindowsOptionalFeature -Online -FeatureName IIS-HttpRedirect
   ```

2. **Use win-acme with IIS integration** (easier):
   - Run `wacs.exe`
   - Choose **M** (More options)
   - Choose **1** (Single binding of an IIS site)
   - Select your IIS site
   - Follow certificate setup

---

## Step 5: Configure WidgetForge for HTTPS (5 minutes)

### Update Your FastAPI Application

1. **Modify main.py** websocket_host line:
   ```python
   "websocket_host": request.headers.get("host", "yourcompany.ddns.net")
   ```

2. **Start with HTTPS support**:
   ```bash
   # If you have certificate files
   uvicorn app.main:app --host 0.0.0.0 --port 443 --ssl-keyfile path/to/privkey.pem --ssl-certfile path/to/cert.pem
   
   # Or keep HTTP on port 8000 and use reverse proxy
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

---

## Step 6: Test Your Setup (5 minutes)

### Basic Connectivity Test

1. **Test DDNS Resolution**:
   ```powershell
   # Should return your public IP
   nslookup yourcompany.ddns.net
   ```

2. **Test HTTP Access**:
   ```
   http://yourcompany.ddns.net:8000/ping
   ```

3. **Test Widget Load**:
   ```
   http://yourcompany.ddns.net:8000/widgets/enhanced-ticker?symbols=EURUSD
   ```

### EVMUX Integration Test

Create a simple HTML test file:

```html
<!DOCTYPE html>
<html>
<head>
    <title>EVMUX Widget Test</title>
</head>
<body>
    <h1>WidgetForge EVMUX Test</h1>
    
    <!-- Basic ticker test -->
    <iframe 
        src="http://yourcompany.ddns.net:8000/widgets/enhanced-ticker?symbols=EURUSD,GBPUSD,BTCUSD"
        width="100%" 
        height="60" 
        frameborder="0"
        style="border: none; overflow: hidden;"
    ></iframe>
    
    <!-- Grid layout test -->
    <iframe 
        src="http://yourcompany.ddns.net:8000/widgets/enhanced-ticker?symbols=EURUSD,GBPUSD,USDJPY,AUDUSD&display_mode=grid&gridColumns=2"
        width="400" 
        height="200" 
        frameborder="0"
        style="border: none; overflow: hidden; margin-top: 20px;"
    ></iframe>
</body>
</html>
```

---

## ⚡ Quick Troubleshooting

### Issue: Domain not resolving
```powershell
# Check current public IP
(Invoke-WebRequest -Uri "http://ipinfo.io/ip").Content.Trim()

# Update DDNS manually (No-IP)
# Login to No-IP dashboard → Dynamic DNS → Modify → Update IP
```

### Issue: Widget not loading
```powershell
# Check if WidgetForge is running
netstat -an | findstr :8000

# Check firewall rules
Get-NetFirewallRule -DisplayName "*WidgetForge*" | Format-Table
```

### Issue: WebSocket not connecting
- Verify port 8000 is open in router
- Check Windows Firewall isn't blocking connections
- Test WebSocket directly: Use browser dev tools → Network tab

---

## 🎯 Final EVMUX URLs

Once setup is complete, your EVMUX embed URLs will be:

### Basic Scrolling Ticker:
```
http://yourcompany.ddns.net:8000/widgets/enhanced-ticker?symbols=EURUSD,GBPUSD,BTCUSD
```

### Professional Grid Layout:
```
http://yourcompany.ddns.net:8000/widgets/enhanced-ticker?symbols=EURUSD,GBPUSD,USDJPY,AUDUSD&display_mode=grid&gridColumns=2&font=Inter&fontSize=18&upColor=%2300ff88&downColor=%23ff4444
```

### With HTTPS (after SSL setup):
```
https://yourcompany.ddns.net/widgets/enhanced-ticker?symbols=EURUSD,GBPUSD
```

---

## 📞 Next Steps After DDNS Setup

1. **Test thoroughly** with different browsers
2. **Contact EVMUX support** to confirm domain compatibility
3. **Set up monitoring** for uptime
4. **Configure auto-renewal** for SSL certificates
5. **Create backup DDNS** with different provider (optional)

## 🆘 Emergency Fallback

If DDNS fails during live stream:
1. Use direct IP: `http://[your-ip]:8000/widgets/enhanced-ticker`
2. Switch to static HTML ticker with cached prices
3. Use mobile hotspot if internet issues

---

**Total Setup Time: ~30 minutes**  
**Confidence Level for EVMUX: 90%+**