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
| Sites          | dc2                                         |


## Provisioning - Config Templates

| Parameter   | Value                                                       |
| ---------   | -------------------------------------------                 |
| **Name**    | h88-config-template-access-switch-cisco                     |
| Data Source | nanog88-hackathon                                           |
| Data File   | jinja-templates/Standard Access Switch Template (Cisco).j2  |
| Auto-sync   | Yes                                                         |

## Devices - Devices

| Parameter       | Value                                         |
| ---------       | -------------------------------------------   |
| **Name**        | dc2-tor-1 / dc2-tor-2 / dc2-tor-3 / dc2-tor-4 |
| Config template | h88-config-template-access-switch-cisco       |
| **Name**        | dc2-spine-1 / dc2-spine-2                     |
| Config template | h88-config-template-access-switch-cisco       |
