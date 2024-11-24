import csv
import requests
from datetime import datetime
from typing import List, Set, Dict

class MullvadIPTracker:
    def __init__(self):
        self.MULLVAD_API_URL = "https://api.mullvad.net/www/relays/all/"
        self.IP_GUIDE_URL = "https://ip.guide/"
        self.IP_FILE = "mullvadips.csv"
        self.SUBNET_FILE = "mullvadsubnets.csv"
        self.current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def fetch_mullvad_data(self) -> List[Dict]:
        response = requests.get(self.MULLVAD_API_URL)
        return response.json()

    def fetch_subnet_for_ip(self, ip: str) -> str:
        try:
            response = requests.get(f"{self.IP_GUIDE_URL}{ip}")
            if response.status_code == 200:
                subnet = response.json().get('network', {}).get('cidr')
                if subnet:
                    return subnet
                raise ValueError("Invalid response format")
            raise ValueError(f"Received status code {response.status_code}")
        except Exception as e:
            print(f"Error fetching subnet for IP {ip}: {e}")
            ip_split = str(ip).split('.')
            return f"{'.'.join(ip_split[:3])}.0/24"

    def get_current_ips(self, data: List[Dict]) -> List[Dict]:
        current_ips = []
        for relay in data:
            for ip_type in ['ipv4_addr_in', 'ipv6_addr_in']:
                if relay[ip_type]:
                    current_ips.append({
                        'ip': relay[ip_type],
                        'hostname': relay['fqdn']
                    })
        return current_ips

    def read_existing_data(self) -> tuple[List[Dict], Set[str]]:
        existing_ip = []
        existing_subnets = set()

        try:
            with open(self.IP_FILE, 'r') as f:
                existing_ip = list(csv.DictReader(f))
        except FileNotFoundError:
            pass

        try:
            with open(self.SUBNET_FILE, 'r') as f:
                existing_subnets = {row[0] for row in csv.reader(f)}
        except FileNotFoundError:
            pass

        return existing_ip, existing_subnets

    def update_ip_data(self, current_ips: List[Dict], existing_data: List[Dict], existing_subnets: Set[str]) -> tuple[List[Dict], Set[str]]:
        updated_data = existing_data

        for ip_entry in current_ips:
            existing_entry = next((item for item in updated_data if item['ip'] == ip_entry['ip']), None)
            
            if ip_entry['ip']:
                ip_subnet = self.fetch_subnet_for_ip(ip_entry['ip'])
                existing_subnets.add(ip_subnet)

            if existing_entry:
                existing_entry['last_seen'] = self.current_time
            else:
                updated_data.append({
                    'ip': ip_entry['ip'],
                    'hostname': ip_entry['hostname'],
                    'first_seen': self.current_time,
                    'last_seen': self.current_time
                })

        return updated_data, existing_subnets

    def write_data_to_files(self, updated_data: List[Dict], existing_subnets: Set[str]):
        with open(self.IP_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ip', 'hostname', 'first_seen', 'last_seen'])
            writer.writeheader()
            writer.writerows(updated_data)

        with open(self.SUBNET_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['subnet'])
            writer.writerows([[subnet] for subnet in existing_subnets])

    def run(self):
        mullvad_data = self.fetch_mullvad_data()
        current_ips = self.get_current_ips(mullvad_data)
        existing_ip, existing_subnets = self.read_existing_data()
        updated_data, updated_subnets = self.update_ip_data(current_ips, existing_ip, existing_subnets)
        self.write_data_to_files(updated_data, updated_subnets)

if __name__ == "__main__":
    tracker = MullvadIPTracker()
    tracker.run()
