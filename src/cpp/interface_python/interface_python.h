#ifndef INTERFACE_PYTHON_H
#define INTERFACE_PYTHON_H

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <pybind11/eigen.h>
#include <pybind11/complex.h>
#include <iostream>
#include "../core/base_data.h"

namespace py = pybind11;

class interface_python
{
public:
    interface_python(double lattice_constant, Matrix3d &lattice_vector);

    ~interface_python();

    void set_HSR(
        int R_num,
        MatrixXd &R_direct_coor,
        int basis_num,
        MatrixXcd &HR_upperTriangleOfDenseMatrix,
        MatrixXcd &SR_upperTriangleOfDenseMatrix);

    void set_HSR_sparse(
        int R_num,
        MatrixXd &R_direct_coor,
        int basis_num,
        SparseMatrixXcdC &HR_upperTriangleOfSparseMatrix,
        SparseMatrixXcdC &SR_upperTriangleOfSparseMatrix);

    void set_rR(
        MatrixXcd &rR_x,
        MatrixXcd &rR_y,
        MatrixXcd &rR_z);

    void set_rR_sparse(
        SparseMatrixXcdC &rR_x,
        SparseMatrixXcdC &rR_y,
        SparseMatrixXcdC &rR_z);

    void set_pR(
        MatrixXcd &pR_x,
        MatrixXcd &pR_y,
        MatrixXcd &pR_z);

    void set_pR_sparse(
        SparseMatrixXcdC &pR_x,
        SparseMatrixXcdC &pR_y,
        SparseMatrixXcdC &pR_z);

    void set_single_atom_position(
        std::string atom_label,
        int na,
        MatrixXd &tau_car);

    void set_single_atom_orb(
        int &atom_index,
        int &nwl,
        std::vector<int> &l_nchi,
        int &mesh,
        double &dr,
        MatrixXd &numerical_orb);

    MatrixXcd &get_HR();

    MatrixXcd &get_SR();

    SparseMatrixXcdC &get_HR_sparse();

    SparseMatrixXcdC &get_SR_sparse();

    MatrixXcd &get_rR(int direction);

    SparseMatrixXcdC &get_rR_sparse(int direction);

    MatrixXcd &get_pR(int direction);

    SparseMatrixXcdC &get_pR_sparse(int direction);

    void update_HR_sparse(SparseMatrixXcdC &HR);

    void update_SR_sparse(SparseMatrixXcdC &SR);

    void update_rR_sparse(int direction, SparseMatrixXcdC &rR_d);

    void update_pR_sparse(int direction, SparseMatrixXcdC &rR_d);

    void get_Hk(
        const MatrixXd &k_direct_coor,
        py::array_t<std::complex<double>> &Hk);

    void get_Sk(
        const MatrixXd &k_direct_coor,
        py::array_t<std::complex<double>> &Sk);

    // void get_HSk_surface(
    //     int direction,
    //     int coupling_layers,
    //     const MatrixXd &k_direct_coor,
    //     py::array_t<std::complex<double>> &Hk00,
    //     py::array_t<std::complex<double>> &Hk01,
    //     py::array_t<std::complex<double>> &Sk00,
    //     py::array_t<std::complex<double>> &Sk01
    // );

    void diago_H(
        const MatrixXd &k_direct_coor,
        py::array_t<std::complex<double>> &eigenvectors,
        py::array_t<double> &eigenvalues);

    void diago_H_eigenvaluesOnly(
        const MatrixXd &k_direct_coor,
        py::array_t<double> &eigenvalues);

    void get_total_berry_curvature_fermi(
        const MatrixXd &k_direct_coor,
        const double &fermi_energy,
        const int mode,
        py::array_t<double> &total_berry_curvature);

    void get_total_berry_curvature_occupiedNumber(
        const MatrixXd &k_direct_coor,
        const int &occupied_band_num,
        const int mode,
        py::array_t<double> &total_berry_curvature);

    // void get_berry_curvature_and_eigenvalues_by_fermi(
    //     const MatrixXd &k_direct_coor,
    //     py::array_t<double> &berry_curvature_values,
    //     py::array_t<double> &eigenvalues,
    //     const double &fermi_energy,
    //     const int mode
    // );

    // void get_berry_curvature_and_eigenvalues_by_occupy(
    //     const MatrixXd &k_direct_coor,
    //     py::array_t<double> &berry_curvature_values,
    //     py::array_t<double> &eigenvalues,
    //     const int &occupied_band_num,
    //     const int mode
    // );

    double get_berry_phase_of_loop(
        const MatrixXd &k_direct_coor_loop,
        const int &occupied_band_num);

    VectorXd get_wilson_loop(
        const MatrixXd &k_direct_coor_loop,
        const int &occupied_band_num);

    void get_optical_conductivity_by_kubo(
        const int &nspin,
        const int &omega_num,
        const double &domega,
        const double &start_omega,
        const double &eta,
        const int &occupied_band_num,
        const MatrixXd &k_direct_coor,
        const int &total_kpoint_num,
        const int &method,
        py::array_t<std::complex<double>> optical_conductivity,
        py::array_t<std::complex<double>> dielectric_function);

    void get_shift_current(
        const int &nspin,
        const int &omega_num,
        const double &domega,
        const double &start_omega,
        const int &smearing_method,
        const double &eta,
        const int &occupied_band_num,
        const MatrixXd &k_direct_coor,
        const int &total_kpoint_num,
        const int &method,
        py::array_t<double> shift_current);

    void get_velocity_matrix(
        const MatrixXd &k_direct_coor,
        py::array_t<double> &eigenvalues,
        py::array_t<std::complex<double>> &eigenvectors,
        py::array_t<std::complex<double>> &velocity_matrix);

    void get_pk_matrix(
        const MatrixXd &k_direct_coor,
        py::array_t<double> &eigenvalues,
        py::array_t<std::complex<double>> &pk_matrix);

    void get_bandunfolding(
        const Matrix3d &M_matrix,
        const MatrixXd &kvect_direct,
        const double &ecut,
        const int &min_bandindex,
        const int &max_bandindex,
        const int &nspin,
        py::array_t<double> &P,
        py::array_t<double> &E);

private:
    base_data Base_Data;
};

#endif
