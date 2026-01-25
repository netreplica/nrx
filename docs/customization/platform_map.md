# Platform Map

The platform map is a YAML file that defines the mapping between values used in NetBox for Device Platforms and the templates to be used when rendering corresponding nodes in the output topology. A [default platform map](https://github.com/netreplica/templates/blob/main/platform_map.yaml) is provided with the copy of Netreplica [`templates`](https://github.com/netreplica/templates), but it can and most likely should be customized by the user to match the actual platforms used in their NetBox instance.

By default, the `nrx` searches the file `platform_map.yaml` in the current directory, and then in the `TEMPLATES_PATH` folders. The path to the file can be overridden using the `--platform-map` argument or the `PLATFORM_MAP` parameter in the [configuration file](CONFIGURATION.md).

## Sections of the platform map file

There are two main sections in the platform map file:

- `platforms` - defines the mapping between NetBox platform names and the node `kind` values for each output format
- `kinds` - defines the mapping between node `kind` values and the templates to be used for each output format

## Platforms section

Example of the `platforms` section where `ubuntu` and `arista-eos` platform names from NetBox are mapped to `linux` and `ceos` node `kind` values for the Containerlab `clab` output format, while `cisco-ios` platform name is mapped to `iosv` node kind for the Cisco Modeling Labs `cml` output format:

```yaml
platforms:
  ubuntu:
    kinds:
      clab: linux
  arista-eos:
    kinds:
      clab: ceos
  cisco-ios:
    kinds:
      cml: iosv
```

## Kinds section

In the `kinds` section, it is possible to define multiple parameters for each node `kind` value. The following subsections describe key use cases.

### Template files

The most important parameters are paths to the template files to render the node, its interface names and, when supported, an interface map. The example below demonstrates how to define the template files for the `ceos` node kind to be used with the Containerlab `clab` output format:

```yaml
kinds:
  clab:
    ceos:
      nodes:
        template: clab/nodes/ceos.j2
      interface_names:
        template: clab/interface_names/default.j2
      interface_maps:
        template: clab/interface_maps/ceos.j2
```

### Image tags

The `image` parameter is useful to override the value of this parameter from the template file. By default, the templates supplied with with `nrx` use image names that have local significance. For example, for `ceos` node kind, the image is `ceos:latest`. A user may choose to tag an actual `ceos` image it has as `ceos:latest` locally. Using the platform map file, an alternative approach becomes possible by providing `image` parameter for the `ceos` node kind:

```yaml
kinds:
  clab:
    ceos:
      nodes:
        template: clab/nodes/ceos.j2
        image: some_corporate_container_registry/ceos:4.28.3M
```

### Other custom kind parameters

Depending on the output format, there could be other parameters that could be used in the templates. In case of Containerlab, there is a set of [generic node parameters](https://containerlab.dev/manual/nodes/) that can be applied to any kind. In the templates supplied with `nrx`, there is a special file `clab/node_params.j2` that can render most of such parameters if included in the node template. In order to activate any of such parameters, define them in the platform map. For examples, use `cmd` parameter to specify the command to be executed after the node is started, or `exec` parameter list for the commands to be executed during the node startup. The example below demonstrates how to override the image for the `linux` node kind and specify a command to be executed after the node is started:

```yaml
kinds:
  clab:
    linux:
      nodes:
        template: clab/nodes/default.j2
        image: netreplica/ubuntu-host:latest
        cmd: /start.sh -sS
        exec:
          - bash -c "echo root:root | chpasswd"
```