import numpy as np
from scipy import integrate
from scipy.interpolate import BSpline
from scipy.optimize import minimize
from Bspline import Bspline


def bending_energy(control_points_flat, t_fixed, fixed_points, k=3):
    """
    Calculates the bending energy of a B-spline curve.
    
    Args:
        control_points_flat: Flattened array of control point coordinates
        t_fixed: Parameter values for the fixed points
        fixed_points: Array of points the spline must pass through
        k: B-spline degree (default: 3 for cubic)
    
    Returns:
        Float representing the bending energy (integral of squared second derivatives)
    """
    # Reshape the flat control points array
    num_points = len(fixed_points)
    num_control = num_points  # Simple case: one control point per fixed point
    control_points = control_points_flat.reshape((num_control, 2))

    # Define knot vector for clamped B-spline
    knots = np.concatenate(([0]*k, np.linspace(0, 1, num_control - k + 1), [1]*k))
    
    # Create the B-spline object
    # Note: BSpline expects coefficients for each dimension separately
    spl_x = BSpline(knots, control_points[:, 0], k, extrapolate=False)
    spl_y = BSpline(knots, control_points[:, 1], k, extrapolate=False)

    # Calculate the second derivative splines
    spl_x_dd = spl_x.derivative(nu=2)
    spl_y_dd = spl_y.derivative(nu=2)

    # Approximate the integral of the squared second derivatives (bending energy)
    # This can be done numerically by sampling over a fine range
    t_sample = np.linspace(0, 1, 200)
    
    # Calculate the squared second derivative magnitude: ||C''(t)||^2 = x''(t)^2 + y''(t)^2
    x_dd_vals = spl_x_dd(t_sample)
    y_dd_vals = spl_y_dd(t_sample)
    
    squared_deriv = x_dd_vals**2 + y_dd_vals**2
    
    # Use the trapezoidal rule for approximate integration
    energy = integrate.trapezoid(squared_deriv, t_sample)
    return energy


def constraint_function(control_points_flat, t_fixed, fixed_points, k=3):
    """
    Defines constraints for the B-spline optimization.
    The curve must pass through the fixed points at specified parameter values.
    
    Args:
        control_points_flat: Flattened array of control point coordinates
        t_fixed: Parameter values for the fixed points
        fixed_points: Array of points the spline must pass through
        k: B-spline degree (default: 3 for cubic)
    
    Returns:
        Array of constraint violations (should be zero at solution)
    """
    num_points = len(fixed_points)
    num_control = num_points
    control_points = control_points_flat.reshape((num_control, 2))
    knots = np.concatenate(([0]*k, np.linspace(0, 1, num_control - k + 1), [1]*k))
    
    spl_x = BSpline(knots, control_points[:, 0], k, extrapolate=False)
    spl_y = BSpline(knots, control_points[:, 1], k, extrapolate=False)

    # The difference between the actual curve point and the required fixed point
    # Should be zero at the constrained locations (t_fixed)
    evaluated_x = spl_x(t_fixed)
    evaluated_y = spl_y(t_fixed)

    return np.concatenate([evaluated_x - fixed_points[:, 0], 
                           evaluated_y - fixed_points[:, 1]])


def minimum_energy_bspline(points, k=3):
    """
    Optimizes a B-spline curve to pass through given points while minimizing bending energy.
    
    Args:
        points: Nx2 array of points the B-spline must pass through
        k: B-spline degree (default: 3 for cubic)
    
    Returns:
        Dictionary containing:
            - 'control_points': Nx2 array of optimized control points
            - 'knots': Knot vector for the B-spline
            - 'degree': B-spline degree (k)
            - 'multiplicities': Array of knot multiplicities
    """
    fixed_points = np.asarray(points)
    num_control = len(fixed_points)
    
    # Corresponding parameter values for the fixed points (normalized [0, 1])
    # Chord-length parameterization: parameter values proportional to cumulative Euclidean distances
    pts = np.asarray(fixed_points)
    if len(pts) < 2:
        t_fixed = np.array([0.0])
    else:
        seg_lengths = np.linalg.norm(pts[1:] - pts[:-1], axis=1)
        cumlen = np.concatenate(([0.0], np.cumsum(seg_lengths)))
        total = cumlen[-1]
        if total <= 0:
            # all points coincide; fall back to uniform spacing
            t_fixed = np.linspace(0.0, 1.0, num_control)
        else:
            t_fixed = cumlen / total
    
    # Initial guess for control points can be the fixed points themselves
    initial_control_points = fixed_points.flatten()
    
    # Constraints dictionary for scipy.optimize.minimize
    # type 'eq' means the constraint expression must equal zero
    constraints = {
        'type': 'eq',
        'fun': constraint_function,
        'args': (t_fixed, fixed_points, k)
    }
    
    # Perform the minimization
    # 'SLSQP' is a suitable method for equality constraints
    result = minimize(
        bending_energy, 
        initial_control_points, 
        args=(t_fixed, fixed_points, k), 
        method='SLSQP', 
        constraints=constraints,
        options={'maxiter': 1000, 'ftol': 1e-6}
    )
    
    # Extract the optimized control points
    optimized_control_points = result.x.reshape(fixed_points.shape)

    optimized_control_points = np.concatenate([[fixed_points[0]], optimized_control_points, [fixed_points[-1]]])

    # Generate knot vector for clamped B-spline
    # For a clamped spline with n control points and degree k:
    # - Knots at endpoints have multiplicity k
    # - Interior knots are placed at the parameter values of the fixed points
    interior_knots = t_fixed[1:-1]  # Exclude the first and last points (already at 0 and 1)
    knots = np.concatenate(([0], interior_knots, [1]))
    1
    # Calculate multiplicities from the knot vector
    unique_knots, multiplicities = np.unique(knots, return_counts=True)
    multiplicities[0] = k + 1
    multiplicities[-1] = k + 1
    
    return Bspline(
        control_points=optimized_control_points,
        multiplicities=multiplicities,
        knots=knots,
        degree=k
    )  


# Example usage
if __name__ == "__main__":
    # Define example points the spline must pass through
    example_points = np.array([
        [0.0, 0.0],
        [2.0, 4.0],
        [5.0, 1.0],
        [7.0, 3.0]
    ])
    
    # Get optimized B-spline definition
    bspline_data = minimum_energy_bspline(example_points)
    
    print("Optimized control points:")
    print(bspline_data['control_points'])
    print("\nKnot vector:")
    print(bspline_data['knots'])
    print("\nDegree:")
    print(bspline_data['degree'])
    print("\nUnique knots:")
    print(bspline_data['unique_knots'])
    print("\nMultiplicities:")
    print(bspline_data['multiplicities'])

