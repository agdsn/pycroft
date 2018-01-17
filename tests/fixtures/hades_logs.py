from . import permissions
from .dummy import host, port


# These datasets contain users with permissions plus a different user
# (from the dummy dataset) who has a host in a connected room (i.e. a
# room with >0 SwitchPatchPorts) making him eglegible for having hades
# logs.
datasets = (
    permissions.datasets
    | {host.HostData, port.SwitchPortData, port.SwitchPatchPortData}
)
