# Windows Server 2019 Setup Guide for EVMUX Integration

This guide will help you configure your Windows Server 2019 to serve the WidgetForge ticker widgets on EVMUX streaming platform.

## Prerequisites

- Windows Server 2019 installed and updated
- Administrator access
- Static IP address or Dynamic DNS configured
- WidgetForge backend already installed and running

## Method 1: Using IIS with URL Rewrite (Recommended)

### Step 1: Install IIS with Required Features

1. Open **Server Manager**
2. Click **Add roles and features**
3. Select **Web Server (IIS)**
4. Under **Web Server Role Services**, ensure these are checked:
   - Common HTTP Features (all)
   - Application Development > WebSocket Protocol
   - Security > Request Filtering
   - Performance > Dynamic Content Compression

### Step 2: Install URL Rewrite Module

1. Download URL Rewrite module from: https://www.iis.net/downloads/microsoft/url-rewrite
2. Run the installer
3. Restart IIS Manager

### Step 3: Configure IIS Site

1. Open **IIS Manager**
2. Right-click **Sites** → **Add Website**
3. Configure:
   - Site name: `WidgetForge`
   - Physical path: `C:\inetpub\wwwroot\widgetforge`
   - Binding: HTTP, Port 80 (we'll add HTTPS later)

### Step 4: Create URL Rewrite Rules

1. Select your site in IIS Manager
2. Double-click **URL Rewrite**
3. Add a new **Reverse Proxy** rule:

```xml
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="ReverseProxyInboundRule1" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://localhost:8000/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_HOST" value="{HTTP_HOST}" />
                        <set name="HTTP_X_FORWARDED_PROTO" value="https" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        <webSocket enabled="true" />
    </system.webServer>
</configuration>
```

### Step 5: Configure WebSocket Support

Add to your web.config:

```xml
<system.webServer>
    <webSocket enabled="true" pingInterval="00:00:10" />
</system.webServer>
```

### Step 6: Install SSL Certificate

1. Use **Let's Encrypt** with win-acme:
   ```powershell
   # Download win-acme
   Invoke-WebRequest -Uri "https://github.com/win-acme/win-acme/releases/download/v2.2.5.1541/win-acme.v2.2.5.1541.x64.pluggable.zip" -OutFile "win-acme.zip"
   Expand-Archive -Path "win-acme.zip" -DestinationPath "C:\tools\win-acme"
   
   # Run certificate wizard
   cd C:\tools\win-acme
   .\wacs.exe
   ```

2. Or use a commercial certificate:
   - Import certificate in IIS Manager
   - Bind to HTTPS (port 443)

### Step 7: Configure CORS Headers

Add to web.config:

```xml
<system.webServer>
    <httpProtocol>
        <customHeaders>
            <add name="Access-Control-Allow-Origin" value="https://evmux.com" />
            <add name="Access-Control-Allow-Methods" value="GET, POST, OPTIONS" />
            <add name="Access-Control-Allow-Headers" value="Content-Type" />
            <add name="Access-Control-Allow-Credentials" value="true" />
        </customHeaders>
    </httpProtocol>
</system.webServer>
```

## Method 2: Direct Port Forwarding (Simple)

### Step 1: Configure Windows Firewall

```powershell
# Run as Administrator
# Allow inbound on port 8000
New-NetFirewallRule -DisplayName "WidgetForge HTTP" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow

# Allow WebSocket connections
New-NetFirewallRule -DisplayName "WidgetForge WebSocket" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

### Step 2: Configure Router/NAT

1. Access your router's admin panel
2. Set up port forwarding:
   - External Port: 8000
   - Internal IP: Your server's local IP
   - Internal Port: 8000
   - Protocol: TCP

### Step 3: Use Dynamic DNS (if no static IP)

1. Sign up for a DDNS service (e.g., No-IP, DuckDNS)
2. Install DDNS client on Windows Server
3. Configure with your DDNS credentials

## Method 3: Using Nginx on Windows

### Step 1: Install Nginx

```powershell
# Download Nginx
Invoke-WebRequest -Uri "http://nginx.org/download/nginx-1.24.0.zip" -OutFile "nginx.zip"
Expand-Archive -Path "nginx.zip" -DestinationPath "C:\nginx"
```

### Step 2: Configure Nginx

Create `C:\nginx\conf\sites\widgetforge.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
    
    # CORS headers for EVMUX
    add_header Access-Control-Allow-Origin "https://evmux.com" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type" always;
    add_header Access-Control-Allow-Credentials "true" always;
}
```

### Step 3: Run Nginx as Service

```powershell
# Install NSSM (Non-Sucking Service Manager)
Invoke-WebRequest -Uri "https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip" -OutFile "nssm.zip"
Expand-Archive -Path "nssm.zip" -DestinationPath "C:\tools"

# Install Nginx as service
C:\tools\nssm-2.24-101-g897c7ad\win64\nssm.exe install nginx C:\nginx\nginx.exe
C:\tools\nssm-2.24-101-g897c7ad\win64\nssm.exe start nginx
```

## Configuring WidgetForge for External Access

### Update main.py

Modify the WebSocket host in your templates to use dynamic host detection:

```python
"websocket_host": request.headers.get("host", "your-domain.com")
```

### Environment Variables

Create `.env` file:

```env
API_KEY=your-secure-api-key
EXTERNAL_HOST=your-domain.com
CORS_ORIGINS=https://evmux.com
```

## Security Considerations

### 1. Rate Limiting

Add rate limiting to prevent abuse:

```powershell
# IIS Dynamic IP Restrictions
Install-WindowsFeature -Name Web-IP-Security
```

### 2. API Key Authentication (Optional)

For widgets requiring authentication:

```python
# In your widget route
api_key = request.query_params.get("api_key")
if api_key != os.getenv("WIDGET_API_KEY"):
    return JSONResponse({"error": "Unauthorized"}, status_code=401)
```

### 3. SSL/TLS Configuration

Ensure strong SSL configuration:
- Use TLS 1.2 or higher
- Disable weak ciphers
- Enable HSTS

## EVMUX Integration

### Basic iframe Embed

```html
<iframe 
    src="https://your-domain.com/widgets/enhanced-ticker?symbols=EURUSD,GBPUSD,BTCUSD&display_mode=scroll"
    width="100%" 
    height="60" 
    frameborder="0"
    style="border: none; overflow: hidden;"
    allow="autoplay"
></iframe>
```

### Advanced Embed with Parameters

```html
<iframe 
    src="https://your-domain.com/widgets/enhanced-ticker?symbols=EURUSD,GBPUSD,XAUUSD&display_mode=grid&bgColor=%23000000&fontColor=%23ffffff&upColor=%2300ff88&downColor=%23ff4444&font=Inter&fontSize=18&showSpread=true&showTimestamp=false&gridColumns=3"
    width="800" 
    height="400" 
    frameborder="0"
    style="border: none; overflow: hidden;"
></iframe>
```

### Responsive Embed

```html
<div style="position: relative; padding-bottom: 10%; height: 0; overflow: hidden;">
    <iframe 
        src="https://your-domain.com/widgets/enhanced-ticker?symbols=EURUSD,GBPUSD&display_mode=scroll"
        style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
        frameborder="0"
    ></iframe>
</div>
```

## Testing Your Setup

### 1. Local Test

```powershell
# Test locally
curl http://localhost:8000/ping

# Test WebSocket
wscat -c ws://localhost:8000/ws/price-stream
```

### 2. External Test

```powershell
# Test from external machine
curl https://your-domain.com/ping

# Test CORS
curl -H "Origin: https://evmux.com" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     https://your-domain.com/widgets/enhanced-ticker
```

### 3. EVMUX Test

Create a test page on EVMUX with your iframe embed and verify:
- Widget loads correctly
- Real-time updates work
- No CORS errors in console
- WebSocket connection established

## Troubleshooting

### Common Issues

1. **WebSocket not connecting**
   - Check firewall rules
   - Verify WebSocket module in IIS
   - Check proxy headers

2. **CORS errors**
   - Verify CORS headers in response
   - Check origin domain matches exactly
   - Ensure credentials are handled correctly

3. **SSL certificate issues**
   - Verify certificate is valid
   - Check certificate chain
   - Ensure proper binding in IIS

### Monitoring

Set up monitoring for:
- Service uptime
- WebSocket connections
- API response times
- Error rates

## Performance Optimization

1. **Enable Compression**
   ```xml
   <system.webServer>
       <urlCompression doStaticCompression="true" doDynamicCompression="true" />
   </system.webServer>
   ```

2. **Cache Static Assets**
   ```xml
   <staticContent>
       <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="7.00:00:00" />
   </staticContent>
   ```

3. **Connection Limits**
   - Adjust IIS connection limits based on expected load
   - Monitor WebSocket connection count

## Maintenance

### Regular Tasks

1. **Certificate Renewal** (if using Let's Encrypt)
   - Set up auto-renewal task in Task Scheduler
   - Test renewal process monthly

2. **Updates**
   - Keep Windows Server updated
   - Update WidgetForge backend regularly
   - Monitor security advisories

3. **Backups**
   - Backup IIS configuration
   - Backup WidgetForge settings
   - Document custom configurations

## Support

For issues specific to:
- **Windows Server**: Check Windows event logs
- **IIS**: Review IIS logs in `C:\inetpub\logs\LogFiles`
- **WidgetForge**: Check application logs
- **EVMUX**: Contact EVMUX support for platform-specific issues