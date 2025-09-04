"""
Direct API Testing for Find My IP Agent

This module contains direct tests for the underlying IPify API and IP-API.com.
"""

import asyncio
import httpx
from datetime import datetime


async def test_ipify_api():
    """Test IPify API directly"""
    print("🌐 Testing IPify API")
    print("=" * 50)
    
    api_url = "https://api.ipify.org?format=json"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url,
                headers={'User-Agent': 'SAM-find_my_ip/1.0.0'},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        ip_address = data.get("ip")
        if ip_address:
            print(f"✅ Successfully retrieved IP: {ip_address}")
            
            # Validate IP format
            parts = ip_address.split('.')
            if len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts):
                print("✅ IP address format is valid")
            else:
                print("❌ IP address format is invalid")
        else:
            print("❌ No IP address found in response")
            
    except Exception as e:
        print(f"❌ IPify API test failed: {e}")


async def test_ip_api_com():
    """Test IP-API.com directly"""
    print("\n🌍 Testing IP-API.com")
    print("=" * 50)
    
    # Test with known IP addresses
    test_ips = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
    
    for ip in test_ips:
        print(f"\nTesting IP: {ip}")
        print("-" * 20)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://ip-api.com/json/{ip}", timeout=10.0)
                response.raise_for_status()
                data = response.json()
            
            if data.get("status") == "success":
                print(f"✅ {ip}: {data.get('country', 'N/A')}, {data.get('city', 'N/A')}")
                print(f"   ISP: {data.get('isp', 'N/A')}")
                print(f"   Timezone: {data.get('timezone', 'N/A')}")
                print(f"   Coordinates: {data.get('lat', 'N/A')}, {data.get('lon', 'N/A')}")
            else:
                print(f"❌ {ip}: API returned error")
                
        except Exception as e:
            print(f"❌ {ip}: Error - {e}")


async def test_ip_api_formats():
    """Test different IP-API.com response formats"""
    print("\n📋 Testing IP-API.com Response Formats")
    print("=" * 50)
    
    test_ip = "8.8.8.8"
    
    # Test JSON format
    print("Testing JSON format...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://ip-api.com/json/{test_ip}", timeout=10.0)
            response.raise_for_status()
            data = response.json()
        
        if data.get("status") == "success":
            print("✅ JSON format works correctly")
            print(f"   Country: {data.get('country', 'N/A')}")
            print(f"   City: {data.get('city', 'N/A')}")
        else:
            print("❌ JSON format failed")
            
    except Exception as e:
        print(f"❌ JSON format test failed: {e}")
    
    # Test XML format
    print("\nTesting XML format...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://ip-api.com/xml/{test_ip}", timeout=10.0)
            response.raise_for_status()
            
        if response.headers.get('content-type', '').startswith('application/xml'):
            print("✅ XML format works correctly")
            print(f"   Content-Type: {response.headers.get('content-type')}")
        else:
            print("⚠️ Unexpected content type for XML")
            
    except Exception as e:
        print(f"❌ XML format test failed: {e}")


async def test_api_rate_limits():
    """Test API rate limiting behavior"""
    print("\n⏱️ Testing API Rate Limits")
    print("=" * 50)
    
    # Test IPify API rate limits
    print("Testing IPify API rate limits...")
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient() as client:
            responses = []
            for i in range(3):  # Be respectful with rate limits
                response = await client.get(
                    "https://api.ipify.org?format=json",
                    headers={'User-Agent': 'SAM-find_my_ip/1.0.0'},
                    timeout=5.0
                )
                responses.append(response.status_code)
                await asyncio.sleep(1)  # Be respectful with delays
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Made 3 IPify requests in {duration:.2f} seconds")
        print(f"   Response codes: {responses}")
        
        if all(code == 200 for code in responses):
            print("✅ All IPify requests successful")
        else:
            print("⚠️ Some IPify requests failed")
            
    except Exception as e:
        print(f"❌ IPify rate limit test failed: {e}")
    
    # Test IP-API.com rate limits
    print("\nTesting IP-API.com rate limits...")
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient() as client:
            responses = []
            for i in range(3):  # Be respectful with rate limits
                response = await client.get(f"http://ip-api.com/json/8.8.8.8", timeout=5.0)
                responses.append(response.status_code)
                await asyncio.sleep(1)  # Be respectful with delays
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Made 3 IP-API.com requests in {duration:.2f} seconds")
        print(f"   Response codes: {responses}")
        
        if all(code == 200 for code in responses):
            print("✅ All IP-API.com requests successful")
        else:
            print("⚠️ Some IP-API.com requests failed")
            
    except Exception as e:
        print(f"❌ IP-API.com rate limit test failed: {e}")


async def test_api_error_handling():
    """Test API error handling"""
    print("\n🚨 Testing API Error Handling")
    print("=" * 50)
    
    # Test invalid IP address
    print("Testing invalid IP address...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://ip-api.com/json/invalid-ip", timeout=10.0)
            
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "fail":
                print("✅ Correctly handled invalid IP address")
            else:
                print("⚠️ Unexpected response for invalid IP")
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Invalid IP test failed: {e}")
    
    # Test private IP address
    print("\nTesting private IP address...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://ip-api.com/json/192.168.1.1", timeout=10.0)
            
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print("✅ Private IP address handled correctly")
            else:
                print("⚠️ Unexpected response for private IP")
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Private IP test failed: {e}")


async def test_response_headers():
    """Test response headers and content types"""
    print("\n📋 Testing Response Headers")
    print("=" * 50)
    
    # Test IPify headers
    print("Testing IPify response headers...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.ipify.org?format=json",
                headers={'User-Agent': 'SAM-find_my_ip/1.0.0'},
                timeout=10.0
            )
            
        content_type = response.headers.get('content-type', '')
        print(f"✅ IPify Content-Type: {content_type}")
        
        if 'application/json' in content_type:
            print("✅ IPify content type is correct")
        else:
            print("⚠️ Unexpected IPify content type")
            
    except Exception as e:
        print(f"❌ IPify header test failed: {e}")
    
    # Test IP-API.com headers
    print("\nTesting IP-API.com response headers...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://ip-api.com/json/8.8.8.8", timeout=10.0)
            
        content_type = response.headers.get('content-type', '')
        print(f"✅ IP-API.com Content-Type: {content_type}")
        
        if 'application/json' in content_type:
            print("✅ IP-API.com content type is correct")
        else:
            print("⚠️ Unexpected IP-API.com content type")
            
    except Exception as e:
        print(f"❌ IP-API.com header test failed: {e}")


async def main():
    """Main test function"""
    print("🌐 Find My IP Agent - Direct API Testing")
    print("=" * 60)
    
    # Run all API tests
    await test_ipify_api()
    await test_ip_api_com()
    await test_ip_api_formats()
    await test_api_rate_limits()
    await test_api_error_handling()
    await test_response_headers()
    
    print("\n" + "=" * 60)
    print("🎉 Direct API testing completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
