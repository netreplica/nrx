Setup

```
git clone https://github.com/netbox-community/Device-Type-Library-Import.git
cd Netbox-Device-Type-Library-Import
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
vim .env
```

Import

```
./nb-dt-import.py --vendors arista,nokia
```