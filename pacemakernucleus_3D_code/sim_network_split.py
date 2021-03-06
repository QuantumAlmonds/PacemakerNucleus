from __future__ import division
from math import sin, cos, pi, isclose
from neuron import h
from os import listdir
from os.path import isfile, join
import os
import sys
import time
import random as rdm
import numpy as np
import pickle as pkl
import FileTree as ft
import PN_Modeling as pnm
import faulthandler
import difflib
import heapq
import tarfile

def trace(frame, event, arg):
    print("%s, %s:%d" % (
    event, frame.f_code.co_filename, frame.f_lineno) + " on PCID:%d" % (
              pc.id()))
    return trace


def network_func(arr):
    """ Evaluates the simulation of the pacemaker nucleus
                with the parameters defined in LoParameters and returns
                the frequency of oscillations.

                @LoParameters: [EK, gKp, gKr]
                @returns: frequency of oscillations either 0 or freq > 0
                """
    LoParameters = arr[0]
    results_index = arr[1]
    start = time.time()
    # NEURON utilities
    h.cvode_active(1)
    h.finitialize(-65)
    h.celsius = 27
    # Biophysical parameters
    ek = LoParameters[0]
    ena = 50
    # Pacemaker cell soma specific
    ps_EL = - 70
    ps_gNa = 1.0
    ps_gK = LoParameters[1]
    ps_gL = 0.0001
    J = 30
    # Pacemaker cell axon specific
    pa_EL = - 70
    pa_gNa = 0.5
    pa_gK = 0.02
    pa_gL = 0.001
    M = 45
    # Relay cell soma specific
    rs_EL = -70
    rs_gNa = 0.75
    rs_gK = LoParameters[2]
    rs_gL = 0.0003
    K = 60
    # Relay cell axon specific
    ra_EL = -70
    ra_gNa = 0.5
    ra_gK = 0.05
    ra_gL = 0.001
    N = 40
    # Synapse Parameters
    conduct_rng = [0.5, 10]  # nS
    # Topology Parameters
    n_pacemakers = 87
    n_relays = 20
    n_p2p_projections = 6
    n_p2r_projections = 7
    # Duration Parameters
    T_STOP = 100  # (ms)
    # Object storage
    pacemaker_cells = []
    relay_cells = []
    pace_network_graph = pnm.Graph()

    # Build Synapse Adjacency List and initialize cell objects.
    for i in range(n_pacemakers + n_relays):
        # num vertices = num cells in network
        pace_network_graph.add_vertex(i)
        if i < n_pacemakers:  # LOOKING AT A PACEMAKER CELL
            p_p_projections = rdm.sample(range(0, n_pacemakers),
                                         n_p2p_projections)
            p_r_projections = rdm.sample(range(n_pacemakers,
                                               n_relays + n_pacemakers),
                                         n_p2r_projections)

            while i in p_p_projections:  # DON'T WANT TO SYNAPSE ONTO SELF
                p_p_projections = rdm.sample(range(0, n_pacemakers),
                                             n_p2p_projections)

            # Now have 2 unique lists of all cells that cell #i synapses to.
            # Add cell i's projections to graph
            all_projections = p_p_projections + p_r_projections
            for proj in all_projections:
                pace_network_graph.add_edge([i, proj])
            pacemaker_cells.append(
                pnm.PacemakerCell([ek, ena, ps_EL, ps_gNa, ps_gK, ps_gL, J],
                                  [ek, ena, pa_EL, pa_gNa, pa_gK, pa_gL, M],
                                  i))

        else:  # LOOKING AT A RELAY CELL
            # Relay cells don't synapse to anything.
            relay_cells.append(
                pnm.RelayCell([ek, ena, rs_EL, rs_gNa, rs_gK, rs_gL, K],
                              [ek, ena, ra_EL, ra_gNa, ra_gK, ra_gL, N],
                              i))
    all_cells = pacemaker_cells + relay_cells
    """
    Orient objects in 3D-space with polar coordinates (position, rotation)
    where the center of the coordinate system corresponds to
    the center of the pacemaker nucleus cell network.

    Default neuronal orientation before repositioning and rotation
    y    z         y
    ^  ^>          ^
    | /            | _______
    |/             |(       )_______________________________________
    |------>  (0,0)+(-So>ma-)______________Axon_____________________----> x
    |              |(_______)
    |              |
    V              v
    """
    t_pace = pacemaker_cells[0]
    t_relay = relay_cells[0]
    len_pace = t_pace.give_len("soma") + t_pace.give_len("axon")
    len_relay = t_relay.give_len("soma") + t_relay.give_len("axon")
    dt_pace = 2 * pi / n_pacemakers
    dt_relay = 2 * pi / n_relays
    # First for relay cells (position, rotation)
    for relay, cell in enumerate(relay_cells):
        cell.set_position((len_relay + 10) * cos(pi + (dt_relay * relay)),
                          (len_relay + 10) * sin(pi + (dt_relay * relay)),
                          0)
        cell.rotateZ(relay * (2 * pi / n_relays))
    # Second for pacemaker cells (position, rotation)
    for pace, cell in enumerate(pacemaker_cells):
        cell.set_position(
            (len_pace + len_relay + 10.001) * cos(pi + (dt_pace * pace)),
            (len_pace + len_relay + 10.001) * sin(pi + (dt_pace * pace)),
            0)
        cell.rotateZ(pace * (2 * pi / n_pacemakers))
    # For dict entries, create a Synapse b/t the key cell & each payload cell.
    for key in pace_network_graph.vertices():
        pre_syn_cell = all_cells[key]
        for ident in pace_network_graph.edges_of_vertex(key):
            post_syn_cell = all_cells[ident]
            pre_syn_cell.add_synapse(post_syn_cell, conduct_rng)

    # Begin simulation of model
    #print(f"Starting simulation {list(LoParameters)} on pc={pc.id()}")
    h.tstop = T_STOP
    h.run()

    """
    Sustained Spontaneous Oscillation (SSO) detection

    First half of sim is EQ period
    Back half is analysis period

    Analysis criteria for SSO:
        - Cells continue firing till end of simulation
        - Cells fire synchronously
        - Cells fire more than once
        - F = 1/T measured from somata
        - At least one cell fires from each population
    """

    continue_firing = False
    has_fired_enough = False
    fire_synchronously = False

    pace_heap = []
    relay_heap = []
    for ident, cell in enumerate(all_cells):
        soma_v, axon_v, t_v = cell.give_spikes()
        soma_voltages = list(soma_v)
        n_spikes = len(soma_voltages)
        if n_spikes > 1:
            f_soma = 1 / (soma_voltages[-1] - soma_voltages[-2])*1000
            if not has_fired_enough:
                has_fired_enough = True
        else:
            f_soma = 0
        if ident < 87:
            heapq.heappush(pace_heap, (f_soma, ident, soma_voltages))
        else:
            heapq.heappush(relay_heap, (f_soma, ident, soma_voltages))
    heapq.heapify(pace_heap)
    heapq.heapify(relay_heap)
    fastest_pace = pace_heap[-1]
    fastest_relay = relay_heap[-1]

    # If freqs > 0 then determine if continue firing
    if fastest_pace[0] > 0 \
            and fastest_relay[0] > 0:
        pace_voltages = fastest_pace[2]
        relay_voltages = fastest_relay[2]
        if (T_STOP - pace_voltages[-1]) < (T_STOP / 3 + 7) \
                and (T_STOP - relay_voltages[-1]) < (T_STOP / 3 + 7):
            continue_firing = True

    if np.isclose(fastest_pace[0], fastest_relay[0], rtol=0.50):
        fire_synchronously = True

    if continue_firing \
            and has_fired_enough \
            and fire_synchronously:
            freq = fastest_relay[0]
    else:
        freq = -1e-15

    end = time.time()
    print(end-start)
    return freq, results_index


def tar_sims(last_sim):
    output_file_name = f"{tarred_dir}/Sims_up_to_{list(last_sim)}"
    only_files = [file for file in listdir(pickled_sims_dir) if
                  isfile(join(pickled_sims_dir, file))]

    with tarfile.open(output_file_name, "w:gz") as tar:
        tar.add(pickled_sims_dir, arcname=os.path.basename(pickled_sims_dir))

    for file in only_files:
        os.remove(f"{pickled_sims_dir}/{file}")


if __name__ == '__main__':
    """
        -Simulate Nodes and update freqs after each sim
            -Each simulation call pickles a Sim object containing the final
            simulation data
                - returns the frequency and the index
                - After 500 simulations completed, an aggregate function is
                 executed which iterates
                through the files in the results directory, combines their data
        """
    h.nrnmpi_init()
    pc = h.ParallelContext()
    #sys.settrace(trace)
    faulthandler.enable()
    h.load_file("nrngui.hoc")
    split_identity = sys.argv[1]
    iteration_identity = sys.argv[2]
    job_id = sys.argv[3]
    SIM_NAME = "network_simulations_3D"
    file_tree = ft.FileTree()

    if int(split_identity) < 128:
        root_identity = 0
    else:
        root_identity = 1
    split_dir = file_tree.get_splits_num_dir(root_identity, iteration_identity,
                                             split_identity)
    results_dir = file_tree.get_split_results_dir(root_identity,
                                                  iteration_identity,
                                                  split_identity)
    pickled_sims_dir = file_tree.get_pickled_sims_dir(root_identity,
                                                      iteration_identity,
                                                      split_identity)
    tarred_dir = file_tree.get_tarred_sim_dir(root_identity, iteration_identity,
                                              split_identity)

    pc.runworker()
    print(f"Job = {job_id}")
    print(f"Split = {split_identity}")
    # Simulation Variables
    node_file = f"{split_dir}/split_{split_identity}.pkl"
    with open(node_file, "rb") as f:
        nodes = pkl.load(f)
    print(f"Loaded {nodes.shape[0]} nodes")
    freqs = np.zeros(nodes.shape[0])
    n_sims_before_aggregate = 20
    num_sims_completed = 0

    for z, node in enumerate(nodes):
        pc.submit(network_func, [node, z])

    while pc.working():
        frequency, idx = pc.pyret()
        freqs[idx] = frequency
        num_sims_completed += 1
        if num_sims_completed % n_sims_before_aggregate == 0:
            tar_sims(nodes[idx])

    results = np.c_[nodes, freqs]
    with open(f"{results_dir}/results_{split_identity}.pkl", "wb") as f:
        pkl.dump(results, f)
        print('File dumped')

    pc.done()
    h.quit()



