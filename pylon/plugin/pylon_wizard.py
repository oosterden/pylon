#------------------------------------------------------------------------------
# Copyright (C) 2009 Richard W. Lincoln
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This software is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANDABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#------------------------------------------------------------------------------

""" Pylon workspace wizard extensions.
"""

#------------------------------------------------------------------------------
#  Imports:
#------------------------------------------------------------------------------

from os.path import dirname, join

from enthought.pyface.api import ImageResource
from envisage.resource.wizard_extension import WizardExtension

#------------------------------------------------------------------------------
#  Constants:
#------------------------------------------------------------------------------

IMAGE_LOCATION = join(dirname(__file__), "..", "ui", "images")

#------------------------------------------------------------------------------
#  "NetworkWizardExtension" class:
#------------------------------------------------------------------------------

class NetworkWizardExtension(WizardExtension):
    """ Contributes a new network wizard.
    """
    # The wizard contribution's globally unique identifier.
    id = "pylon.plugin.new_network_wizard"

    # Human readable identifier
    name = "Network"

    # The wizards's image (displayed on selection etc)
    image = ImageResource("new", search_path=[IMAGE_LOCATION])

    # The class of contributed wizard
    wizard_class = "pylon.plugin.pylon_network_wizard:NetworkWizard"

    # A longer description of the wizard's function
    description = "Create a new network resource"

# EOF -------------------------------------------------------------------------