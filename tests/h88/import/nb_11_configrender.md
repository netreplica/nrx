# Device Configuration Rendering Setup

## Operations - Data Sources

| Parameter   | Value                                           |
| ---------   | -------------------------------------------     |
| Name        | nanog88-hackathon                               |
| Type        | Git                                             |
| URL         | https://github.com/netreplica/nanog88-hackathon |
| Enabled     | Yes                                             |


## Provisioning - Config Contexts

| Parameter      | Value                                       |
| ---------      | ------------------------------------------- |
| Name           | h88-config-context                          |
| Weight         | 1000                                        |
| Active         | Yes                                         |
| Data Source    | nanog88-hackathon                           |
| Data File      | config-context/example-config-context.json  |
| Auto-sync      | Yes                                         |
| **Assignment** |                                             |
| Sites          | HQ                                          |


## Provisioning - Config Templates

| Parameter   | Value                                                       |
| ---------   | -------------------------------------------                 |
| Name        | h88-config-template-access-switch-cisco                     |
| Data Source | nanog88-hackathon                                           |
| Data File   | jinja-templates/Standard Access Switch Template (Cisco).j2  |
| Auto-sync   | Yes                                                         |


## Devices - Devices

| Parameter       | Value                                       |
| ---------       | ------------------------------------------- |
| Name            | HQ-Switch1                                  |
| Config template | h88-config-template-access-switch-cisco |

## Devices - Devices - Device Interfaces

| Device        | Interface               | Type        | 802.1Q Mode | Untagged VLAN | Tagged VLANs   | LAG              |
| ------        | ---------               | -----       | ----------- | ------------- | -------------  | ---------------- |
| HQ-Switch1    | GigabitEthernet1/0/1    |             | Access      | 200           |                |                  |
| HQ-Switch1    | GigabitEthernet1/0/2    |             | Access      | 100           |                |                  |
| HQ-Switch1    | GigabitEthernet1/0/3    |             | Access      | 100           |                |                  |
| HQ-Switch1    | GigabitEthernet1/0/4    |             | Access      | 100           |                |                  |
| HQ-Switch1    | GigabitEthernet1/0/5    |             | Access      | 100           |                |                  |
| HQ-Switch1    | Vlan900                 | Virtual     |             |               |                |                  |
| HQ-Switch1    | Port-Channel10          | LAG         | Tagged      |               | 100, 200, 900  |                  |
| HQ-Switch1    | TenGigabitEthernet1/1/1 | SFP+ (10GE) | Access      | 200           |                | Port-Channel10   |
| HQ-Switch1    | TenGigabitEthernet1/1/2 | SFP+ (10GE) | Access      | 100           |                | Port-Channel10   |
