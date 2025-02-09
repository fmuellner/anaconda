#
# Kickstart module for URL payload source.
#
# Copyright (C) 2020 Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
from pyanaconda.core.constants import URL_TYPE_BASEURL, URL_TYPE_METALINK, URL_TYPE_MIRRORLIST, \
    URL_TYPES
from pyanaconda.core.signal import Signal
from pyanaconda.core.payload import ProxyString, ProxyStringError
from pyanaconda.modules.common.errors.general import InvalidValueError
from pyanaconda.modules.common.structures.payload import RepoConfigurationData
from pyanaconda.modules.payloads.constants import SourceType, SourceState
from pyanaconda.modules.payloads.source.source_base import PayloadSourceBase, RPMSourceMixin
from pyanaconda.modules.payloads.source.url.url_interface import URLSourceInterface
from pyanaconda.modules.payloads.source.utils import has_network_protocol

from pyanaconda.anaconda_loggers import get_module_logger
log = get_module_logger(__name__)


class URLSourceModule(PayloadSourceBase, RPMSourceMixin):
    """The URL source payload module."""

    REPO_NAME_ID = 0

    def __init__(self):
        super().__init__()
        self._repo_configuration = RepoConfigurationData()
        self.repo_configuration_changed = Signal()

    def __repr__(self):
        return "Source(type='URL', url='{}')".format(self._repo_configuration.url)

    def for_publication(self):
        """Get the interface used to publish this source."""
        return URLSourceInterface(self)

    def get_state(self):
        """Get state of this source."""
        return SourceState.NOT_APPLICABLE

    @property
    def type(self):
        """Get type of this source."""
        return SourceType.URL

    @property
    def description(self):
        """Get description of this source."""
        return self._repo_configuration.url

    @property
    def network_required(self):
        """Does the source require a network?

        :return: True or False
        """
        return has_network_protocol(self._repo_configuration.url)

    @property
    def required_space(self):
        """The space required for the installation.

        :return: required size in bytes
        :rtype: int
        """
        return 0

    def process_kickstart(self, data):
        """Process the kickstart data."""
        repo_data = RepoConfigurationData()

        if data.url.url:
            repo_data.url = data.url.url
            repo_data.type = URL_TYPE_BASEURL
        elif data.url.mirrorlist:
            repo_data.url = data.url.mirrorlist
            repo_data.type = URL_TYPE_MIRRORLIST
        elif data.url.metalink:
            repo_data.url = data.url.metalink
            repo_data.type = URL_TYPE_METALINK

        repo_data.proxy = data.url.proxy
        repo_data.ssl_verification_enabled = not data.url.noverifyssl
        repo_data.ssl_configuration.ca_cert_path = data.url.sslcacert or ""
        repo_data.ssl_configuration.client_cert_path = data.url.sslclientcert or ""
        repo_data.ssl_configuration.client_key_path = data.url.sslclientkey or ""

        self.set_repo_configuration(repo_data)

    def setup_kickstart(self, data):
        """Setup the kickstart data."""
        if self.repo_configuration.type == URL_TYPE_BASEURL:
            data.url.url = self.repo_configuration.url
        elif self.repo_configuration.type == URL_TYPE_MIRRORLIST:
            data.url.mirrorlist = self.repo_configuration.url
        elif self.repo_configuration.type == URL_TYPE_METALINK:
            data.url.metalink = self.repo_configuration.url

        data.url.proxy = self.repo_configuration.proxy
        data.url.noverifyssl = not self.repo_configuration.ssl_verification_enabled
        data.url.sslcacert = self.repo_configuration.ssl_configuration.ca_cert_path
        data.url.sslclientcert = self.repo_configuration.ssl_configuration.client_cert_path
        data.url.sslclientkey = self.repo_configuration.ssl_configuration.client_key_path

        data.url.seen = True

    def generate_repo_configuration(self):
        """Generate RepoConfigurationData structure."""
        return self.repo_configuration

    def set_up_with_tasks(self):
        """Set up the installation source.

        :return: list of tasks required for the source setup
        :rtype: [Task]
        """
        return []

    def tear_down_with_tasks(self):
        """Tear down the installation source.

        :return: list of tasks required for the source clean-up
        :rtype: [Task]
        """
        return []

    @property
    def repo_configuration(self):
        """Get repository configuration data.

        :rtype: RepoConfigurationData data structure
        """
        return self._repo_configuration

    def set_repo_configuration(self, repo_configuration):
        """Set repository configuration data.

        :param repo_configuration: configuration for this repository
        :type repo_configuration: RepoConfigurationData data structure
        """
        self._validate_url(repo_configuration.type)
        self._validate_proxy(repo_configuration.proxy)

        self._repo_configuration = repo_configuration
        self.repo_configuration_changed.emit(self._repo_configuration)
        log.debug("The repo_configuration is set to %s", self._repo_configuration)

    def _validate_proxy(self, proxy):
        if not proxy:
            return

        try:
            ProxyString(url=proxy)
        except ProxyStringError as e:
            raise InvalidValueError("Proxy URL does not have valid format: {}".format(str(e))) \
                from e

    def _validate_url(self, url_type):
        if url_type not in URL_TYPES:
            raise InvalidValueError("Invalid source type set '{}'".format(url_type))
