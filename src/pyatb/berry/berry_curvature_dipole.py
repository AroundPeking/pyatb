from pyatb import RANK, COMM, SIZE, OUTPUT_PATH, RUNNING_LOG, timer
from pyatb.constants import elem_charge_SI, hbar_SI, Ang_to_Bohr
from pyatb.kpt import kpoint_generator
from pyatb.integration import adaptive_integral
from pyatb.integration import grid_integrate_3D
from pyatb.tb import tb
from pyatb.parallel import op_gather_numpy
import numpy as np
import os
import shutil
from mpi4py import MPI
class Berry_Curvature_Dipole:
    def __init__(
        self,
        tb:tb,
        integrate_mode,
        **kwarg
    ):
        if tb.nspin == 2:
            raise ValueError('BCD only for nspin = 1 or 4 !')

        self.__tb = tb
        self.__max_kpoint_num = tb.max_kpoint_num
        self.__tb_solver = tb.tb_solver

        self.__k_start = np.array([0.0, 0.0, 0.0], dtype=float)
        self.__k_vect1 = np.array([1.0, 0.0, 0.0], dtype=float)
        self.__k_vect2 = np.array([0.0, 1.0, 0.0], dtype=float)
        self.__k_vect3 = np.array([0.0, 0.0, 1.0], dtype=float)

        output_path = os.path.join(OUTPUT_PATH, 'Berry_Curvature_Dipole')
        if RANK == 0:
            path_exists = os.path.exists(output_path)
            if path_exists:
                shutil.rmtree(output_path)
                os.mkdir(output_path)
            else:
                os.mkdir(output_path)

        self.output_path = output_path
        
        if RANK == 0:
            with open(RUNNING_LOG, 'a') as f:
                f.write('\n')
                f.write('\n------------------------------------------------------')
                f.write('\n|                                                    |')
                f.write('\n|                 Berry Curvature Dipole                   |')
                f.write('\n|                                                    |')
                f.write('\n------------------------------------------------------')
                f.write('\n\n')
        if integrate_mode != 'Grid':
            raise ValueError('Since the integration is of a tensor, only Grid integrate_mode is available.')
        self.set_parameters(**kwarg)
    def get_constant(self):
        v1 = self.__tb.direct_to_cartesian_kspace(self.__k_vect1)
        v2 = self.__tb.direct_to_cartesian_kspace(self.__k_vect2)
        v3 = self.__tb.direct_to_cartesian_kspace(self.__k_vect3)
        V = np.linalg.det(np.array([v1.T,v2.T,v3.T]))
        c =  V /(2*np.pi)**3
        return c
    def set_parameters(
        self, 
        omega, 
        domega, 
        integrate_grid, 
        adaptive_grid, 
        adaptive_grid_threshold,
        **kwarg):
        
        self.__start_omega = omega[0]
        self.__end_omega = omega[1]
        self.__domega = domega
        self.__omega_num = int((self.__end_omega - self.__start_omega) / domega ) + 1
        self.__integrate_grid = integrate_grid
        self.__adaptive_grid = adaptive_grid
        self.__adaptive_grid_threshold = adaptive_grid_threshold
        if RANK == 0:
            with open(RUNNING_LOG, 'a') as f:
                f.write('\nParameter setting : \n')
                f.write(' >> omega    : %-8.4f %-8.4f\n' % (self.__start_omega, self.__end_omega))
                f.write(' >> domega   : %-10.6f\n' % (self.__domega))
                f.write(' >> integrate_grid          : %-8d %-8d %-8d\n' %(self.__integrate_grid[0], self.__integrate_grid[1], self.__integrate_grid[2]))
                f.write(' >> adaptive_grid           : %-8d %-8d %-8d\n' %(self.__adaptive_grid[0], self.__adaptive_grid[1], self.__adaptive_grid[2]))
                f.write(' >> adaptive_grid_threshold : %-10.4f\n' %(self.__adaptive_grid_threshold))
    def calculate_berry_curvature_dipole(self,**kwarg):
        constant1 = self.get_constant()
        constant2 = 1/(self.__integrate_grid[0]*self.__integrate_grid[1]*self.__integrate_grid[2])
        data = self.__area_judge(
            self.__k_start,
            self.__k_vect1,
            self.__k_vect2,
            self.__k_vect3,
            self.__integrate_grid,
            self.__adaptive_grid_threshold)
        self.bcd_0 = data[0]
        kpoint_list1 = data[1]
        kpoint_num1 = kpoint_list1.shape[0]
        
        k_vect12 = self.__k_vect1/(self.__integrate_grid[0])
        k_vect22 = self.__k_vect2/(self.__integrate_grid[1])
        k_vect32 = self.__k_vect3/(self.__integrate_grid[2])
        delta = k_vect12+k_vect22+k_vect32
        if RANK == 0:
            
            np.savetxt(os.path.join(self.output_path, 'kpoint_list'), kpoint_list1, fmt='%0.8f')
            #np.savetxt(os.path.join(self.output_path, 'bcd_step1.dat'), self.bcd_0*constant1*constant2, fmt='%0.8f')
        for i in range(kpoint_num1):
            k_generator = self.__set_k_mp(kpoint_list1[i,:]-delta/2,k_vect12,k_vect22,k_vect32,self.__adaptive_grid)
            bcd_total = np.zeros([self.__omega_num,9],dtype = float)
            for ik in k_generator:
                ik_process = kpoint_generator.kpoints_in_different_process(SIZE, RANK, ik)
                k_direct_coor = ik_process.k_direct_coor_local
                kpoint_num = ik_process.k_direct_coor_local.shape[0]

                bcd_pl = self.get_bcd_pl(k_direct_coor)
                bcd_local = bcd_pl.sum(axis=0)
                
                bcd_temp = COMM.reduce(bcd_local, root = 0, op=MPI.SUM)
                if RANK == 0:
                    bcd_total = bcd_total+bcd_temp
            bcd_total =  COMM.bcast(bcd_total, root=0)
            self.bcd_0 = self.bcd_0+bcd_total/(self.__adaptive_grid[0]*self.__adaptive_grid[1]*self.__adaptive_grid[2])
            
        if RANK == 0:
            
            self.print_data(self.bcd_0*constant1*constant2)
            
            
            
            
        return
    def print_data(self,data):
        output_path = self.output_path
        np.savetxt(os.path.join(output_path, 'bcd.dat'), data, fmt='%0.8f')
        return
    def print_plot_script(self):
        output_path = os.path.join(self.output_path, '')
        with open(os.path.join(output_path, 'plot_bcd.py'), 'w') as f:
            bcd_file = os.path.join(output_path, 'bcd.dat')
            

            plot_script = """import numpy as np
import matplotlib.pyplot as plt
direction = {{
    'xx' : 1,
    'xy' : 2,
    'xz' : 3,
    'yx' : 4,
    'yy' : 5,
    'yz' : 6,
    'zx' : 7,
    'zy' : 8,
    'zz' : 9
}}
data = np.loadtxt('{bcd_file}')


x = np.linspace({E_min},{E_max},{E_num})

smearing = 1e-3
def partial_f(smearing,E):
    
    temp = np.exp((E)/smearing)
    ans = temp/((1+temp)**2 *smearing )
    return ans
    
num = {E_num}
data_smear = np.zeros([num,9],dtype = float)
for i in range(num):
    for j in range(num):
        
        data_smear[i,:] = data_smear[i,:]+data[j,:]*partial_f(smearing,(x[i]-x[j]))
for key, value in direction.items():
    figure = plt.figure()
    plt.title('Berry Curvature Dipole')
    plt.xlim(x[0], x[-1])
    plt.xlabel('$\omega (eV)$')
    plt.ylabel('$BCD_{{%s}} $'%(key))
    
    plt.plot(x, data_smear[:,value-1], color='b', linewidth=1, linestyle='-')
    plt.legend()
    plt.savefig('{output_path}' + 'bcd-%s.pdf'%(key))
    plt.close('all')
    
    
""".format(bcd_file=bcd_file, E_min=self.__start_omega, E_max=self.__end_omega, E_num = self.__omega_num, output_path=output_path)

            f.write(plot_script)

    def get_bcd_pl(self,k_direct_coor):
        E_min = self.__start_omega
        E_max = self.__end_omega
        E_num = self.__omega_num
        E_list = np.linspace(E_min,E_max,E_num)
        
        #then the contribution would not be considered
        
        delta_E = (E_max-E_min)/E_num
        matrix_dim = self.__tb.basis_num
        k_direct_coor = np.array(k_direct_coor,dtype = float)
        kpoint_num = k_direct_coor.shape[0]
        bcd_pl = np.zeros([kpoint_num,int(E_num),9],dtype = float)
        
        
        eigenvalues,eigenvectors,velocity_matrix = self.__tb_solver.get_velocity_matrix(k_direct_coor)
        
        
        #print('Rank %d calculate velocity matrix, time cost: %f'%(RANK,(end-start)))
        #####################################
        for ik in range(kpoint_num):
            
            for nband in range(matrix_dim):
                E = eigenvalues[ik,nband]
                
                n = int((E-E_min)/delta_E)
                if n <= (E_num-1)and n>=0:
                    
                    #calculate berry curvature for single nband
                    E_bar = 1e-4
                    bc_nband = np.zeros(3,dtype = float)
                    for iband in range(matrix_dim):
                        E_in = np.abs(eigenvalues[ik,iband]-E)
                        C = E_in**2
                        if np.abs(E_in)>E_bar:
                            bc_nband[0] +=\
                            ((velocity_matrix[ik,1,nband,iband]*velocity_matrix[ik,2,iband,nband])*2j/C).real
                            bc_nband[1] += \
                            ((velocity_matrix[ik,2,nband,iband]*velocity_matrix[ik,0,iband,nband])*2j/C).real
                            bc_nband[2] += \
                            ((velocity_matrix[ik,0,nband,iband]*velocity_matrix[ik,1,iband,nband])*2j/C).real
                            
                    bcd_pl[ik,n,0]+=(velocity_matrix[ik,0,nband,nband]*bc_nband[0]).real
                    bcd_pl[ik,n,1]+=(velocity_matrix[ik,0,nband,nband]*bc_nband[1]).real
                    bcd_pl[ik,n,2]+=(velocity_matrix[ik,0,nband,nband]*bc_nband[2]).real
                    bcd_pl[ik,n,3]+=(velocity_matrix[ik,1,nband,nband]*bc_nband[0]).real
                    bcd_pl[ik,n,4]+=(velocity_matrix[ik,1,nband,nband]*bc_nband[1]).real
                    bcd_pl[ik,n,5]+=(velocity_matrix[ik,1,nband,nband]*bc_nband[2]).real
                    bcd_pl[ik,n,6]+=(velocity_matrix[ik,2,nband,nband]*bc_nband[0]).real
                    bcd_pl[ik,n,7]+=(velocity_matrix[ik,2,nband,nband]*bc_nband[1]).real
                    bcd_pl[ik,n,8]+=(velocity_matrix[ik,2,nband,nband]*bc_nband[2]).real
                else:
                    continue
                    
                    
        #####################################
        
        #print('Rank %d calculate bcd for %d kpoints, time cost: %f'%(RANK,kpoint_num,(end-start)))
        return bcd_pl
    def __area_judge(
        self, 
        k_start,
        k_vect1,
        k_vect2,
        k_vect3,
        grid,
        bar,
        ):
        
        #search for kpoints in a given area 
        #whose band land on a given energy range 
        #whose bcd above a certain bar
        E_min = self.__start_omega
        E_max = self.__end_omega
        E_num = self.__omega_num
        matrix_dim = self.__tb.basis_num
        k_generator = self.__set_k_mp(k_start,k_vect1,k_vect2,k_vect3,grid)
        
        fermi_points_total = np.zeros([0,3],dtype = float)
        bcd_total = np.zeros([E_num,9],dtype = float)
        bcd_total_ = np.zeros([E_num,9],dtype = float)
        for ik in k_generator:
            
            fermi_points = np.zeros([0,3],dtype = float)
            ik_process = kpoint_generator.kpoints_in_different_process(SIZE, RANK, ik)
            k_direct_coor = ik_process.k_direct_coor_local
            kpoint_num = ik_process.k_direct_coor_local.shape[0]
            
            
            bcd_pl = self.get_bcd_pl(k_direct_coor)
            
            bcd_local = bcd_pl.sum(axis=0)
            bcd_local_ = bcd_local
            for i in range(kpoint_num):
                
                flag = 0
                if np.max(bcd_pl[i,:,:])>=bar or np.min(bcd_pl[i,:,:])<=-bar:
                    flag = 1
                    bcd_local -= bcd_pl[i,:,:]
                    
                if flag:
                    fermi_points = np.r_[fermi_points,np.array([k_direct_coor[i,:]])]
            fermi_points_local = COMM.reduce(fermi_points, root=0,op=op_gather_numpy)
            bcd_temp = COMM.reduce(bcd_local, root = 0, op=MPI.SUM)
            bcd_temp_ = COMM.reduce(bcd_local_, root = 0, op=MPI.SUM)
            if RANK == 0:
                
                fermi_points_total = np.r_[fermi_points_total,fermi_points_local]
                bcd_total = bcd_total+bcd_temp
                bcd_total_ = bcd_total_+bcd_temp_
        fermi_points_total = COMM.bcast(fermi_points_total, root=0)
        bcd_total =  COMM.bcast(bcd_total, root=0)
        #if RANK == 0:
            #np.savetxt(os.path.join(self.output_path, 'bcd_step0.dat'), bcd_total_, fmt='%0.8f')
        return [bcd_total,fermi_points_total]
    def __set_k_mp(
        self,
        k_start,
        k_vect1,
        k_vect2,
        k_vect3,
        mp_grid
    ):
        k_generator = kpoint_generator.mp_generator(self.__max_kpoint_num, k_start, k_vect1,k_vect2, k_vect3, mp_grid)
        return k_generator
    
    def __set_k_direct(self, kpoint_direct_coor, **kwarg):
        k_generator = kpoint_generator.array_generater(self.__max_kpoint_num, kpoint_direct_coor)
        return k_generator