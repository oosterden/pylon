#------------------------------------------------------------------------------
# Copyright (C) 2007 Richard W. Lincoln
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

""" Defines functions returning admittance and susceptance matrices. """

#------------------------------------------------------------------------------
#  Imports:
#------------------------------------------------------------------------------

import logging

from cvxopt.base import matrix, spmatrix, sparse, spdiag, gemv, exp, mul, div

#------------------------------------------------------------------------------
#  Logging:
#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

#------------------------------------------------------------------------------
#  "make_susceptance_matrix" function:
#------------------------------------------------------------------------------

def make_susceptance_matrix(network):
    """ Returns the susceptance and source bus susceptance matrices for the
    given network.

    """

    buses = network.non_islanded_buses
    branches = network.in_service_branches
    n_buses = network.n_non_islanded_buses
    n_branches = network.n_in_service_branches

    # Create an empty sparse susceptance matrix.
    # http://abel.ee.ucla.edu/cvxopt/documentation/users-guide/node32.html
    b = spmatrix([], [], [], (n_buses, n_buses))

    # Make an empty sparse source bus susceptance matrix
    b_source = spmatrix([], [], [], (n_branches, n_buses))

    # Filter out branches that are out of service
#        active_branches = [e for e in branches if e.in_service]

    for e in branches:
        e_idx = branches.index(e)
        # Find the indexes of the buses at either end of the branch
        src_idx = buses.index(e.source_bus)
        dst_idx = buses.index(e.target_bus)

        # B = 1/X
        if e.x != 0.0: # Avoid zero division
            b_branch = 1/e.x
        else:
            # infinite susceptance for zero reactance branch
            b_branch = 1e12#numpy.Inf

        # Divide by the branch tap ratio
        if e.ratio != 0.0:
            b_branch /= e.ratio

        # Off-diagonal matrix elements (i,j) are the negative
        # susceptance of branches between buses[i] and buses[j]
        b[src_idx, dst_idx] += -b_branch
        b[dst_idx, src_idx] += -b_branch
        # Diagonal matrix elements (k,k) are the sum of the
        # susceptances of the branches connected to buses[k]
        b[src_idx, src_idx] += b_branch
        b[dst_idx, dst_idx] += b_branch

        # Build Bf such that Bf * Va is the vector of real branch
        # powers injected at each branch's "source" bus
        b_source[e_idx, src_idx] = b_branch
        b_source[e_idx, dst_idx] = -b_branch

    logger.debug("Built branch susceptance matrix:\n%s" % b)

    logger.debug("Built source bus susceptance matrix:\n%s" % b_source)

    return b, b_source

#------------------------------------------------------------------------------
#  "make_admittance_matrix" function:
#------------------------------------------------------------------------------

def make_admittance_matrix(network):
    """ Returns an admittance matrix for the supplied network. """

    buses = network.non_islanded_buses
    n_buses = network.n_non_islanded_buses
    branches = network.in_service_branches

    Y = spmatrix([], [], [], size=(n_buses, n_buses), tc="z")

    for br in branches:
        src_idx = buses.index(br.source_bus)
        dst_idx = buses.index(br.target_bus)
        # y = 1/(R+jX) + (G+jB)/2
        # The conductance (G) is considered negligble
        try:
            y = 1/(complex(br.r, br.x))
        except ZeroDivisionError:
#            print 'WW: zero division'
            # if the branch has zero resistance and reactance then
            # the admittance is infinite
            y = 1e10
#        print 'y', y
        chrg = complex(0, br.b)/2
        # off-diagonal matrix elements (i,j) are the negative
        # admittance of branches between buses[i] and buses[j]

        # TODO: find out why the shunt admittance is not added
        # to off-diagonal elements.
        Y[src_idx, dst_idx] += -y
        Y[dst_idx, src_idx] += -y
        # diagonal matrix elements (k,k) are the sum of the
        # admittances of the branches connected to buses[k]
        Y[src_idx, src_idx] += y + chrg
        Y[dst_idx, dst_idx] += y + chrg

        # TODO: investigate why the imaginary componenets of the admittance
        # matrix are slightly different to this from MATPOWER
    return Y

#------------------------------------------------------------------------------
#  "AdmittanceMatrix" class:
#------------------------------------------------------------------------------

class AdmittanceMatrix:
    """ Build sparse Y matrix. """

    # Network represented by the matrix
    network = None

    # Sparse admittance matrix.
    Y = spmatrix

    def __init__(self, network):
        """ Returns a new AdmittanceMatrix instance. """

        self.network = network


    def build(self):
        """ Builds the admittance matrix.

        Cf =

             1     1     1     0     0     0     0     0     0     0     0
             0     0     0     1     1     1     1     0     0     0     0
             0     0     0     0     0     0     0     1     1     0     0
             0     0     0     0     0     0     0     0     0     1     0
             0     0     0     0     0     0     0     0     0     0     1
             0     0     0     0     0     0     0     0     0     0     0


        Ct =

             0     0     0     0     0     0     0     0     0     0     0
             1     0     0     0     0     0     0     0     0     0     0
             0     0     0     1     0     0     0     0     0     0     0
             0     1     0     0     1     0     0     0     0     0     0
             0     0     1     0     0     1     0     1     0     1     0
             0     0     0     0     0     0     1     0     1     0     1

        """

        j = 0+1j
        network = self.network
        base_mva = network.mva_base
        buses = network.non_islanded_buses
        n_buses = network.n_non_islanded_buses
        branches = network.in_service_branches

        in_service = matrix([e.in_service for e in branches])

        # Series admittance.
        # Ys = stat ./ (branch(:, BR_R) + j * branch(:, BR_X))
        r = matrix([e.r for e in branches])
        x = matrix([e.x for e in branches])
        Ys = div(in_service, (r + j*x))

        # Line charging susceptance
        # Bc = stat .* branch(:, BR_B);
        b = matrix([e.b for e in branches])
        Bc = mul(in_service, b)

        # Default tap ratio = 1
        # Transformer off nominal turns ratio ( = 0 for lines ) (taps at "from"
        # bus, impedance at 'to' bus, i.e. ratio = Vf / Vt)"
        ratio = matrix([e.ratio for e in branches])
        # Phase shifters
        # tap = tap .* exp(j*pi/180 * branch(:, SHIFT));
        phase_shift = matrix([e.phase_shift for e in branches])

        # Ytt = Ys + j*Bc/2;
        # Yff = Ytt ./ (tap .* conj(tap));
        # Yft = - Ys ./ conj(tap);
        # Ytf = - Ys ./ tap;
        Ytt = Ys + j*Bc/2
        Yff = div(Ytt, (mul(ratio, conj(ratio))))
        Yft = div(-Ys, conj(ratio))
        Ytf = div(-Ys, ratio)

        # Connection matrices.
        source_bus = matrix([buses.index(v) for v in buses])
        target_bus = matrix([buses.index(v) for v in buses])
        Cf = spmatrix(1, I=source_bus, J=range(n_branches), size=(n_buses, n_branches), tc="i")

        # Shunt admittance
        # Ysh = (bus(:, GS) + j * bus(:, BS)) / baseMVA;
        g_shunt = matrix([v.g_shunt for v in buses])
        b_shunt = matrix([v.b_shunt for v in buses])
        Ysh = (g_shunt + j * b_shunt) / base_mva

        Y = spmatrix([], [], [], size=(n_buses, n_buses), tc="z")

#------------------------------------------------------------------------------
#  "SusceptanceMatrix" class:
#------------------------------------------------------------------------------

class SusceptanceMatrix:
    """ Build sparse B matrices

    The bus real power injections are related to bus voltage angles by
        P = Bbus * Va + Pbusinj

    The real power flows at the from end the lines are related to the bus
    voltage angles by
        Pf = Bf * Va + Pfinj

    TODO: Speed up by using spdiag(x)

    """

    # Network represented by the matrix
    network = None

    # Suceptance matrix
    B = spmatrix

    # Source bus susceptance matrix
    B_source = spmatrix

    def __init__(self, network):
        """ Returns a new SusceptanceMatrix instance """

        self.network
        self.B, self.B_source = self.build()


    def build(self):
        """ Build the matrices """

        if self.network is None:
            logger.error("network unspecified")
            return
        else:
            network = self.network

        buses = network.buses
        branches = network.branches
        n_buses = network.n_buses
        n_branches = network.n_branches

        # Create an empty sparse susceptance matrix.
        # http://abel.ee.ucla.edu/cvxopt/documentation/users-guide/node32.html
        b = spmatrix([], [], [], (n_buses, n_buses))

        # Make an empty sparse source bus susceptance matrix
        b_source = spmatrix([], [], [], (n_branches, n_buses))

        # Filter out branches that are out of service
#        active_branches = [e for e in branches if e.in_service]

        for e in branches:
            e_idx = branches.index(e)
            # Find the indexes of the buses at either end of the branch
            src_idx = buses.index(e.source_bus)
            dst_idx = buses.index(e.target_bus)

            # B = 1/X
            if e.x != 0.0: # Avoid zero division
                b_branch = 1/e.x
            else:
                # infinite susceptance for zero reactance branch
                b_branch = 1e12#numpy.Inf

            # Divide by the branch tap ratio
            if e.ratio != 0.0:
                b_branch /= e.ratio

            # Off-diagonal matrix elements (i,j) are the negative
            # susceptance of branches between buses[i] and buses[j]
            b[src_idx, dst_idx] += -b_branch
            b[dst_idx, src_idx] += -b_branch
            # Diagonal matrix elements (k,k) are the sum of the
            # susceptances of the branches connected to buses[k]
            b[src_idx, src_idx] += b_branch
            b[dst_idx, dst_idx] += b_branch

            # Build Bf such that Bf * Va is the vector of real branch
            # powers injected at each branch's "source" bus
            b_source[e_idx, src_idx] = b_branch
            b_source[e_idx, dst_idx] = -b_branch

        logger.debug("Built branch susceptance matrix:\n%s" % b)

        logger.debug("Built source bus susceptance matrix:\n%s" % b_source)

        return b, b_source

#------------------------------------------------------------------------------
#  "AdmittanceMatrix" class:
#------------------------------------------------------------------------------

class PSATAdmittanceMatrix:

    def build(self, network):
        j = 0 + 1j
        buses = network.non_islanded_buses
        n_buses = network.n_non_islanded_buses
        branches = network.in_service_branches

        y = spmatrix([], [], [], size=(n_buses, n_buses), tc='z')

#        source_idxs = [e.source_bus for e in branches]
#        target_idxs = [e.target_bus for e in branches]
#
#        z = []
#        for e in branches:
#            if e.x != 0 and e.r != 0:
#                z.append(1/complex(e.r, e.x))
#            else:
#                z.append(Inf)
#
#        charge = [0.5*complex(0, e.b) for e in branches]
#
#        ts = [e.ratio*exp(j*e.phase_shift*pi/180) for e in branches]

        # TODO: Test speed increase with matrix algebra implementation
        for e in branches:
            source_idx = buses.index(e.source_bus)
            target_idx = buses.index(e.target_bus)

            # y = 1/(R+jX) + (G+jB)/2
            # The conductance (G) is considered negligible
            try: #avoid zero division
                z = 1/(complex(e.r, e.x))
            except ZeroDivisionError:
                z = complex(0, 1e09) #infinite admittance for zero reactance

            # Shunt admittance
            charge = complex(0, e.b)/2

            ts = e.ratio*exp(j*(e.phase_shift*pi/180))
            ts2 = ts*conjugate(ts)

            # off-diagonal matrix elements (i,j) are the negative
            # admittance of branches between buses[i] and buses[j]
            # TODO: Establish why PSAT does it this way
            y[source_idx, target_idx] += -z*ts
            y[target_idx, source_idx] += -z*conjugate(ts)
            # diagonal matrix elements (k,k) are the sum of the
            # admittances of the branches connected to buses[k]
            y[source_idx, source_idx] += z+charge
            y[target_idx, target_idx] += z*ts2+charge

        return y

# EOF -------------------------------------------------------------------------
