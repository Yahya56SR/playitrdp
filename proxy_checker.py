import requests
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_proxy(proxy, test_url, timeout):
    """Test if a proxy is working by making a request through it"""
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }
    
    try:
        response = requests.get(
            test_url,
            proxies=proxies,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        
        if response.status_code == 200:
            return proxy, True, f"Success! Response IP: {response.json().get('origin', 'N/A')}"
        return proxy, False, f"Failed - Status code: {response.status_code}"
        
    except Exception as e:
        return proxy, False, f"Error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='Proxy Tester')
    parser.add_argument('proxy_file', help='Path to proxy file (ip:port format)')
    parser.add_argument('--test-url', default='http://httpbin.org/ip',
                        help='URL to test proxies against (default: http://httpbin.org/ip)')
    parser.add_argument('--timeout', type=int, default=10,
                        help='Request timeout in seconds (default: 10)')
    parser.add_argument('--threads', type=int, default=20,
                        help='Number of concurrent threads (default: 20)')
    parser.add_argument('--output', default='working_proxies.txt',
                        help='Output file for working proxies (default: working_proxies.txt)')
    args = parser.parse_args()

    # Read proxies from file
    with open(args.proxy_file) as f:
        proxies = [line.strip() for line in f if line.strip()]
    
    if not proxies:
        print("No proxies found in the file.")
        return

    print(f"Testing {len(proxies)} proxies against {args.test_url}...\n")
    
    working_proxies = []
    total = len(proxies)
    tested = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        future_to_proxy = {
            executor.submit(test_proxy, proxy, args.test_url, args.timeout): proxy
            for proxy in proxies
        }
        
        for future in as_completed(future_to_proxy):
            tested += 1
            proxy, status, message = future.result()
            
            if status:
                working_proxies.append(proxy)
                result = "WORKING"
            else:
                failed += 1
                result = "FAILED"
            
            print(f"[{tested}/{total}] {proxy} - {result}: {message}")
    
    # Save working proxies
    with open(args.output, 'w') as f:
        f.write("\n".join(working_proxies))
    
    print(f"\nResults:")
    print(f"Total proxies: {total}")
    print(f"Working proxies: {len(working_proxies)}")
    print(f"Failed proxies: {failed}")
    print(f"Working proxies saved to: {args.output}")

if __name__ == "__main__":
    main()
