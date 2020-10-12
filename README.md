# N-dimensional parameter simulation of a neural network on a super computer.
Our algorithm works in two main steps, the iteration step and the surface following step. The first of the two is given a coarse grid of parameter combinations represented as cartesian coordinates, and a simulation is run for each coordinate combination. The result of the simulation is a frequency value generated by the behavior detection algorithm (a value > 0 if the behavior is present, or -1e-15 if the behavior is not present). Adjacent cubes in the n-dimensional parameter space are compared and where their values differ in sign (+ vs -), the parameter space is refined by half and a new set of parameter combinations are generated which will be simulated in the next iteration. After a number of iterations have been run resulting in a final grid resolution fine enough to interpolate a surface, the surface following step is begun. In this step, the grid is no longer refined, but the boundary between positive and negative frequency values is extended until it becomes a closed boundary. Following this step, the data can be extracted and plotted to show the surface defining the boundary of the behavior in the parameter space. 

# User Requirements:
- Access to the Discovery Cluster
- Proficiency in Python
- An understanding of the NEURON simulation environment
- Proficiency with git and the command line

Discovery cluster access can be obtained here https://rc-docs.northeastern.edu/en/latest/get_started/get_access.html.
Follow Discovery's Documentation for getting acquainted with the different types of hardware and software that are available for use. Additionally, read the section on how to use Slurm, which is software that allows you to monitor and schedule jobs to be run on the cluster.

# Clone this repository locally:
cd ~/Directory_where_you_want_to_store_the_code
git clone git@github.com:QuantumAlmonds/PacemakerNucleus.git

Once this command finishes, you will have a copy of the project saved locally to your directory. 

# Setup a working directory on the cluster:
ssh username@login.discovery.neu.edu
enter password
cd /scratch/cluster_username
mkdir N_Dimensional_Simulations
exit

# Transfer the project from the local directory to the remote directory:
scp Directory_where_you_want_to_store_the_code/PacemakerNucleus cluster_username@login.discovery.neu.edu:/scratch/cluster_username/N_Dimensional_Simulations

Once this file transfer is complete, we can begin modifying the code on the cluster to match our project specifications. 

# Setting the parameter space variables:
In Initialize_grid.py, ensure the following:
current_step = 0
sim_name = "name_of_simulations"

Indices of sol_range correspond to indices of num_div.
sol_range = [[0, 1], [0, 1], [0, 1], ...] where the zeros and ones are replaces with the boundaries of the respective parameter ranges. 
num_div = [X, Y, Z, ...] where X, Y, Z, and successive values represent one fewer than the number of points along each respective range.

# Modifying the modelled network:
In PN_Modeling.py, modify the PacemakerCell and RelayCell classes to match the geometry and biophysics of your cell types.
Using the NEURON simulation module, design an algorithm to generate the topology of your network. Place this algorithm into the sim_network_split.py module replacing lines 83 - 114. 

# Modifying the behavior detection algorithm:
Each cell in your network contains information about the times of action potentials generated during simulation. Obtain this data via the give_spikes() method in the PacemakerCell and RelayCell classes and use it to design an algorithm that accurately detects the desired behavior. The current aglorithm in place detects sustained, spontaneous oscillations. Replace lines 171-207 with your algorithm and return a positive value if the behavior is present, and -1e-15 if the behavior is not present.

# Running your first iteration:

# Running successive iterations:

# Running surface following:

# Extracting the data from the cluster:

# Plotting the surface:
