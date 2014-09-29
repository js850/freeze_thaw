import pickle
import argparse

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import numpy as np
import matplotlib.pyplot as plt

from pele.systems import LJCluster, BLJCluster

sa_base = declarative_base()

class BHTrajectory(sa_base):
    __tablename__ = 'tbl_bh_trajectory'
    _id = sa.Column(sa.Integer, primary_key=True)
    system = sa.Column(sa.String)
    minimum_energy_trajectory = sa.Column(sa.PickleType)
    energy_trajectory = sa.Column(sa.PickleType)
    minimum_energy_found = sa.Column(sa.Float)
    trajectory_length = sa.Column(sa.Integer)

class BHTrajDatabase(object):
    def __init__(self, db=":memory:", connect_string='sqlite:///%s'):

        # set up the engine which will manage the backend connection to the database
        self.engine = sa.create_engine(connect_string%(db), echo=False)

        # set the schema        
        conn = self.engine.connect()
        sa_base.metadata.create_all(bind=self.engine)
        conn.close()

        
        # set up the session which will manage the frontend connection to the database
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.connection = self.engine.connect()
    
    def get_trajectories(self, system="lj75"):
        candidates = self.session.query(BHTrajectory).filter(BHTrajectory.system==system)
        return candidates
    
    def add_trajectory(self, system, minE, etraj):
        traj = BHTrajectory()
        traj.system = system
        traj.minimum_energy_trajectory = minE
        traj.minimum_energy_found = minE[-1]
        traj.trajectory_length = len(minE)
        traj.energy_trajectory = etraj
        self.session.add(traj)
        self.session.commit()


def do_bh_run(system, db, n_minimizations=1000):
    system.params.structural_quench_params.tol = 1e-2
    bh = system.get_basinhopping(db, max_n_minima=10)
    bh.setPrinting(frq=100)
    
    minE = []
    etraj = []
    for i in xrange(n_minimizations):
        bh.run(1)
        minE.append(db.get_lowest_energy_minimum().energy)
        etraj.append(bh.markovE)
    return np.array(minE), np.array(etraj)



def main(system_name="lj75", n_minimizations=20000):
    if system_name == "lj75":
        system = LJCluster(75)
    elif system_name == "blj100":
        system = BLJCluster(100, epsAB=1., epsBB=1., sigBB=1.3, sigAB=2.3/2)
    elif system_name == "blj30":
        system = BLJCluster(30, epsAB=1., epsBB=1., sigBB=1.3, sigAB=2.3/2)
    else:
        raise ValueError()
    db = system.create_database()
    
    
    tdb = BHTrajDatabase("bh_traj_new.sqlite")
    
    if False:
        minE_list = pickle.load(open(picklef, "rb"))
        for minE in minE_list:
            tdb.add_trajectory(system_name, minE)
    
    if False:
        for traj in tdb.get_trajectories(system_name):
            print traj.trajectory_length, traj.minimum_energy_found
        return
    
    minE, etraj = do_bh_run(system, db, n_minimizations=n_minimizations)
    tdb.add_trajectory(system_name, minE, etraj)

    print "minimum energies found"
    for traj in tdb.get_trajectories(system_name):
        print traj.trajectory_length, traj.minimum_energy_found
    
    colors = ["black", "red", "blue", "green", "red", "cyan", "magenta"]
    for i, traj in enumerate(tdb.get_trajectories(system_name)):
        c = colors[i%len(colors)]
        
        plt.plot(traj.minimum_energy_trajectory, color=c)
        plt.plot(traj.energy_trajectory, ':', color=c)
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", type=str, default="blj100",
                        help="system class name")
    parser.add_argument("--niter", type=int, default=1000,
                        help="number of basinhopping iterations")
    args = parser.parse_args()
    
    
    main(system_name=args.system, n_minimizations=args.niter)