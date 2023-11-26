# Platform Map

The platform map is a YAML file that defines the mapping between values used in NetBox for Device Platforms and the templates to be used when rendering corresponding nodes in the output topology. A default platform map is provided with the `templates`, but it can and most likely should be customized by the user to match the actual platforms used in their NetBox instance.

The file is searched for in the current directory, and then in the `TEMPLATES_PATH` folders. The path to the file can be overridden using the `--platform-map` argument or the `PLATFORM_MAP` environmental variable.

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

In the `kinds` section, it is possible to define multiple parameters for each node `kind` value. The key parameters are paths to the template files to render the node, its interface names and, when supported, an interface map. Equally important is the ability to override a value of the `image` parameter used in the template file.

### Custom kind images

By default, the templates supplied with with `nrx` use image names that have local significance. For example, for `ceos` node kind, the image is `ceos:latest`. A user may choose to tag an actual `ceos` image it has as `ceos:latest` locally. Using the platform map file, an alternative approach becomes possible by providing `image` parameter for the `ceos` node kind:

```yaml
kinds:
  clab:
    ceos:
      nodes:
        template: clab/nodes/ceos.j2
        image: some_corporate_container_registry/ceos:4.28.3M
      interface_names:
        template: clab/interface_names/default.j2
      interface_maps:
        template: clab/interface_maps/ceos.j2
```

### Other custom kind parameters