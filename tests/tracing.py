import os
import pynetbox

nb_api_url = os.getenv('NB_API_URL')
nb_api_token = os.getenv('NB_API_TOKEN')
nb_site = os.getenv('NB_SITE')
nb_role = os.getenv('NB_ROLE')

nb = pynetbox.api(url=nb_api_url, token=nb_api_token)

# Get site id from NetBox
site = nb.dcim.sites.get(name=nb_site)
# Get all devices from NetBox
devices = nb.dcim.devices.filter(site_id=site.id,role=[nb_role])

# Iterate through each device and check its connections
for device in devices:
    print(f"Device '{device}' interface traces")
    traces = []
    # Get the device's connections using the interface tracing API
    for interface in list(nb.dcim.interfaces.filter(device_id=device.id)):
        if interface.connected_endpoint:
            trace = interface.trace()
            if len(trace) > 0:
                traces.append(trace)
                if len(trace[0]) == 1 and len(trace[-1]) == 1:
                    int_a = trace[0][0]
                    int_b = trace[-1][0]
                    if isinstance(int_a, pynetbox.models.dcim.Interfaces) and isinstance(int_b, pynetbox.models.dcim.Interfaces):
                        print(f"{int_a.device} {int_a.name} <-> {int_b.device} {int_b.name}")