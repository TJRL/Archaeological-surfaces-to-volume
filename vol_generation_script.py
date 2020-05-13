# This is a script made to calculate the volume between different surfaces
# of archaeological excavation grounds. It implements different methods to do
# so. The surfaces are triangle meshes.
#
# Made by Bram Dekker (11428279) of the Univeristy of Amsterdam as a bachelor
# thesis.

import bpy
import bmesh
import mathutils
import time
import math
import numpy as np
import itertools
from plyfile import PlyData, PlyElement
import sys
sys.setrecursionlimit(2500)

C = bpy.context
D = bpy.data

RED = (1, 0, 0, 1)
GREEN = (0, 1, 0, 1)
BLUE = (0, 0, 1, 1)
YELLOW = (1, 1, 0, 1)
ORANGE = (1, 0.5, 0, 1)
PURPLE = (0.5, 0, 1, 1)
PINK = (1, 0.4, 1, 1)
GREY = (0.5, 0.5, 0.5, 1)
BLACK = (0, 0, 0, 1)
WHITE = (1, 1, 1, 1)
RGBAS = [RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, PINK, BLACK, WHITE, GREY]


def init(test=False):
    """Initialize the scene by removing the cube, camera and light and import
    and orientate the trench objects."""
    if test:
        clear_scene()
    else:
        remove_volumes()
        rotate_objects()


def is_volume(obj):
    """Check if object is a generated volume or not."""
    if (obj.name.startswith("triangle_mesh") or
            obj.name.startswith("cubic") or obj.name.startswith("tetra")):
        return True

    return False


def remove_volumes():
    """Remove the generated volumes from the last script run."""
    vols = [obj for obj in D.objects if is_volume(obj)]
    for vol in vols:
        D.meshes.remove(vol.data)


def clear_scene():
    """Clear the scene from all objects."""
    if C.active_object is not None and C.active_object.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    for m in D.meshes:
        D.meshes.remove(m)

    for obj in D.objects:
        D.objects.remove(obj, do_unlink=True)


def rotate_objects():
    """Rotate the objects back to their normal form, no rotation at all"""
    for name in D.objects:
        name.rotation_euler = (0.0, 0.0, 0.0)


def bounding_box(name=None):
    """Find the minimum and maximum x, y and z-coordinates."""
    min_x = min_y = min_z = math.inf
    max_x = max_y = max_z = -math.inf
    if name:
        obj_list = [D.meshes[name]]
    else:
        obj_list = D.meshes

    for obj in obj_list:
        for v in obj.vertices:
            if v.co[0] < min_x:
                min_x = v.co[0]
            if v.co[0] > max_x:
                max_x = v.co[0]
            if v.co[1] < min_y:
                min_y = v.co[1]
            if v.co[1] > max_y:
                max_y = v.co[1]
            if v.co[2] < min_z:
                min_z = v.co[2]
            if v.co[2] > max_z:
                max_z = v.co[2]

    return min_x, max_x, min_y, max_y, min_z, max_z


def translate_to_origin(min_x, max_x, min_y, max_y, min_z, max_z):
    """Translate the objects to around the origin to get better insight."""
    x_trans = -(min_x + (max_x - min_x) / 2)
    y_trans = -(min_y + (max_y - min_y) / 2)
    z_trans = -(min_z + (max_z - min_z) / 2)

    if (x_trans, y_trans, z_trans) == (0, 0, 0):
        return 0, 0, 0

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.transform.translate(value=(x_trans, y_trans, z_trans))
    bpy.ops.object.transform_apply()
    bpy.ops.object.select_all(action="DESELECT")

    return x_trans, y_trans, z_trans


def update_minmax(minx, maxx, miny, maxy, minz, maxz, difx, dify, difz):
    """Update the minimum and maximum values based on the translation to the
    origin."""
    minx, maxx = minx + difx, maxx + difx
    miny, maxy = miny + dify, maxy + dify
    minz, maxz = minz + difz, maxz + difz
    return minx, maxx, miny, maxy, minz, maxz


def print_bbox(minx, maxx, miny, maxy, minz, maxz):
    """Print the minimum and maximum values of the data to gain a better
    understanding of the data."""
    print("Min x, max x: {min_x}, {max_x}\nMin y, max y: {min_y}, {max_y}"
          "\nMin z, max z: {min_z}, {max_z}".format(
              min_x=minx, max_x=maxx, min_y=miny, max_y=maxy, min_z=minz,
              max_z=maxz))


def print_total_volume(volume):
    """Print the total volume."""
    print("The total volume is %.2f cm3 or %.2f m3.\n" %
          (volume, volume / 1000000))


def print_num_primitives(num_x, num_y, num_z):
    """Print the number of primitives in all directions."""
    print("Number of primitives in x-direction: %d, y-direction: %d and "
          "z-direction: %d" % (num_x, num_y, num_z))


def print_primitive_size(length, width, height):
    """Print the size of the primitive used."""
    print("Primitive size: %.2f x %.2f x %.2f cm" % (length, width, height))


def print_layer_volume(test, volume):
    """Print the layer volume only if it is not a test run."""
    if not test:
        print("This layer has a volume of %.2f cm3 or %.2f m3" %
              (volume, volume / 1000000))


# Start of the space-oriented algorithm.
def ordered_meshes(selected_meshes):
    """Return the list of indices in de bpy.data.objects list of all
    objects from high to low (highest avg z-coordinate of vertices)."""
    mesh_list = []

    for obj in selected_meshes:
        cur_avg = np.average([vt.co[2] for vt in obj.data.vertices.values()])
        mesh_list.append((cur_avg, D.objects.values().index(obj)))
        obj.select_set(False)

    return [elem[1] for elem in sorted(mesh_list, reverse=True)]


def dist_btwn_pts(p1, p2):
    """Calculate the distance between 2 points in 3D space."""
    x_dif, y_dif, z_dif = p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]
    return math.sqrt(x_dif**2 + y_dif**2 + z_dif**2)


def center_tetrahedron(v1, v2, v3, v4):
    """Return the center of a tetrahedron with vertices v1, v2, v3 and v4."""
    s = tuple(map(sum, zip(v1, v2, v3, v4)))
    return tuple(el / 4 for el in s)


def make_voxel_verts(origin, length, width, height):
    """Make a list of vertices for given origin and sizes."""
    v0 = origin
    v1 = (origin[0] + length, origin[1], origin[2])
    v2 = (origin[0], origin[1] + width, origin[2])
    v3 = (origin[0] + length, origin[1] + width, origin[2])
    v4 = (origin[0], origin[1], origin[2] + height)
    v5 = (origin[0] + length, origin[1], origin[2] + height)
    v6 = (origin[0], origin[1] + width, origin[2] + height)
    v7 = (origin[0] + length, origin[1] + width, origin[2] + height)
    return [v0, v1, v2, v3, v4, v5, v6, v7]


def make_voxel_faces(i):
    """Make a list of faces for given vertices of a cube."""
    f1 = (i, i + 1, i + 3, i + 2)
    f2 = (i + 4, i + 5, i + 7, i + 6)
    f3 = (i, i + 2, i + 6, i + 4)
    f4 = (i + 1, i + 3, i + 7, i + 5)
    f5 = (i, i + 1, i + 5, i + 4)
    f6 = (i + 2, i + 3, i + 7, i + 6)
    return [f1, f2, f3, f4, f5, f6]


def draw_cubes(origins, length, width, height, rgba):
    """Draw cubes from given origins, size and color"""
    # Specify the color and faces for the new meshes.
    color = D.materials.new("Layer_color")
    index = 0
    verts, faces = [], []

    for o in origins:
        # Make the vertices of the new mesh.
        vs = make_voxel_verts(o, length, width, height)
        verts.extend(vs)
        faces.extend(make_voxel_faces(index))
        index += 8

    # Create a new mesh.
    mesh = D.meshes.new("cubic_volume")
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()

    # Create new object and give it data.
    new_object = D.objects.new("cubic_volume", mesh)
    new_object.data = mesh

    # Put object in the scene.
    C.collection.objects.link(new_object)
    C.view_layer.objects.active = new_object
    new_object.select_set(True)

    # Give the object the color rgba and deselect it.
    C.active_object.data.materials.append(color)
    C.object.active_material.diffuse_color = rgba
    new_object.select_set(False)


def make_tetra_faces(i):
    """Return a list of 4 faces based on the vertex index."""
    f1 = (i, i + 1, i + 2)
    f2 = (i, i + 1, i + 3)
    f3 = (i, i + 2, i + 3)
    f4 = (i + 1, i + 2, i + 3)
    return [f1, f2, f3, f4]


def draw_tetrahedra(vertices, rgba):
    """Draw tetrahedra from given vertices and color."""
    # Specify the color and faces for the new meshes.
    color = D.materials.new("Layer_color")

    verts, faces = [], []
    index = 0

    for vs in vertices:
        verts.extend(vs)
        faces.extend(make_tetra_faces(index))
        index += 4

    # Create new mesh structure.
    mesh = D.meshes.new("tetrahedron_volume")
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()

    # Create new object and give it data.
    new_object = D.objects.new("tetrahedron_volume", mesh)
    new_object.data = mesh

    # Put object in the scene.
    C.collection.objects.link(new_object)
    C.view_layer.objects.active = new_object
    new_object.select_set(True)

    # Give the object the color rgba and deselect it.
    C.active_object.data.materials.append(color)
    C.object.active_material.diffuse_color = rgba
    new_object.select_set(False)


def cast_down_ray(mesh, var, cur, h, dr="x"):
    """Cast a ray from (x,y,h) or (y,x,h) in direction (0, 0, -1),
    straight downwards."""
    if dr == "x":
        result = D.objects[mesh].ray_cast((cur, var, h), (0, 0, -1))
    elif dr == "y":
        result = D.objects[mesh].ray_cast((var, cur, h), (0, 0, -1))

    return result


def find_direction_minmax(msh1, msh2, threshold, minc, maxc, maxz,
                          stepsize, cast_hgt, cur_min, cur_max, dr="x"):
    """Find the minimum and maximum coordinate in a specific direction for
    which the threshold is exceeded."""
    # Initialize minimum and maximum found to false.
    min_found, max_found = False, False

    while not (min_found and max_found):
        # For variable c value, check if current value and this c is a position
        # that exceeds threshold.
        for c in np.linspace(minc, maxc, 50):
            if not min_found:
                # Cast rays to both meshes from cast height downward.
                min1_ray = cast_down_ray(msh1, cur_min, c, cast_hgt, dr=dr)
                min2_ray = cast_down_ray(msh2, cur_min, c, cast_hgt, dr=dr)

                # Check if both rays hit the meshes and check distance between
                # the hit locations.
                if (min1_ray[0] and min2_ray[0] and
                        dist_btwn_pts(min1_ray[1], min2_ray[1]) >= threshold):
                    min_found = True
                    min_c = cur_min

            if not max_found:
                # Cast rays to both meshes from cast height downward.
                max1_ray = cast_down_ray(msh1, cur_max, c, cast_hgt, dr=dr)
                max2_ray = cast_down_ray(msh2, cur_max, c, cast_hgt, dr=dr)

                # Check if both rays hit the meshes and check distance between
                # the hit locations.
                if (max1_ray[0] and max2_ray[0] and
                        dist_btwn_pts(max1_ray[1], max2_ray[1]) >= threshold):
                    max_found = True
                    max_c = cur_max

        # Increase minimum and decrease maximum with every step.
        cur_min += stepsize
        cur_max -= stepsize

    return min_c, max_c


def reduce_boundingbox(mesh1, mesh2, threshold, minx, maxx, miny, maxy, maxz):
    """Reduce the bounding box for 2 meshes so that only (x,y)-positions with
    relatively large vertical distance are in it. Mesh1 lays above mesh2."""
    # Set the stepsize, cast height and current minimum and maximum values.
    stepsize = 0.01
    cast_hgt = maxz + 1
    cur_minx, cur_maxx = minx, maxx
    cur_miny, cur_maxy = miny, maxy

    # Find new minimum and maximum x-values based on the threshold.
    minx, maxx = find_direction_minmax(
        mesh1, mesh2, threshold, miny, maxy, maxz, stepsize, cast_hgt,
        cur_minx, cur_maxx, dr="x")

    # Find new minimum and maximum y-values based on the threshold.
    miny, maxy = find_direction_minmax(
        mesh1, mesh2, threshold, minx, maxx, maxz, stepsize, cast_hgt,
        cur_miny, cur_maxy, dr="y")

    print("New bounding box: minx %.2f, maxx %.2f, miny %.2f, maxy %.2f" %
          (minx, maxx, miny, maxy))
    return minx, maxx, miny, maxy


def set_vol_primitive(length, width, height, primitive):
    """Calculate the volume of the specified primitive in cubic centimetres."""
    if primitive == "voxel":
        vol_primitive = length * width * height * 1000000
    elif primitive == "tetra":
        vol_primitive = 1000000 * (length * width * height) / 6

    return vol_primitive


def check_outside_mesh(upper_mesh, center, max_distance):
    """Check if center lays outside closed mesh or not."""
    hit = True
    hit_count = 0
    cast_point = center
    adder = (0, 0, 0.001)

    # Cast rays as long as it hits the mesh. Count the amount of times the ray
    # hits the mesh.
    while hit:
        cast_result = D.objects[upper_mesh].ray_cast(
            cast_point, (0, 0, 1), distance=max_distance)

        if cast_result[0]:
            hit_count += 1
            cast_point = tuple(sum(x) for x in zip(cast_result[1], adder))
        else:
            hit = False

    # If there are an even amount of hits, center is not inside the closed
    # mesh and thus True is returned.
    return (hit_count % 2) == 0


def decide_in_volume(upper_mesh, lower_mesh, center, max_distance, threshold,
                     closed_mesh):
    """Decide if the primitive on the given position belongs to the volume
    between the meshes."""
    if closed_mesh and check_outside_mesh(upper_mesh, center, max_distance):
        return False

    # Cast ray up to upper mesh and ray down to lower mesh.
    res_up = D.objects[upper_mesh].ray_cast(
        center, (0, 0, 1), distance=max_distance)
    res_down = D.objects[lower_mesh].ray_cast(
        center, (0, 0, -1), distance=max_distance)

    # If both rays hit the mesh, centroid is in between the meshes.
    if (res_up[0] and res_down[0] and
            dist_btwn_pts(res_up[1], res_down[1]) >= threshold):
        in_volume = True
    else:
        in_volume = False

    return in_volume


def make_point_list(minx, maxx, miny, maxy, minz, maxz, l, w, h):
    """Make a list of cartesian points between boundaries."""
    # Make lists for x, y and z-coordinates that divide up the bounding box.
    xs = np.arange(minx, maxx + l, l)
    ys = np.arange(miny, maxy + w, w)
    zs = np.arange(minz, maxz + h, h)

    # Combine the coordinates to 3D Cartesian coordinates.
    return [(x, y, z) for x in xs for y in ys for z in zs]


def make_vol_prims_centers(tetra_array):
    """For each primitive corners in the array, transform it to its center."""
    centers = [center_tetrahedron(*verts) for verts in tetra_array]
    return centers


def process_voxel(
        x, y, z, l, w, h, upper_mesh, lower_mesh, max_distance,
        volume_primitives, vol_primitive, threshold, closed_mesh):
    """Determine if voxel is part of the volume or not."""
    # Initialize volume to zero.
    volume = 0
    upper_mesh, lower_mesh = update_indices(upper_mesh, lower_mesh, "cubic")

    # Determine center of voxel.
    center = (x+l/2, y+w/2, z+h/2)

    # Decide if voxel is part of the volume.
    in_volume = decide_in_volume(
        upper_mesh, lower_mesh, center, max_distance, threshold,
        closed_mesh)

    # If the voxel is part of the volume, add it to the primitive list and set
    # the volume.
    if in_volume:
        volume_primitives.append((x, y, z))
        volume = vol_primitive

    return volume


def process_tetra(
        x, y, z, l, w, h, upper_mesh, lower_mesh, max_distance,
        volume_primitives, vol_primitive, threshold, closed_mesh):
    """Determine if tetra is part of the volume or not."""
    # Initialize volume to zero.
    volume = 0
    upper_mesh, lower_mesh = update_indices(upper_mesh, lower_mesh, "tetra")

    # Get all vertices for the 6 tetrahedra.
    v1, v2 = (x, y, z), (x + l, y + w, z + h)
    other_vs = [(x+l, y, z), (x+l, y+w, z), (x, y+w, z), (x, y+w, z+h),
                (x, y, z+h), (x+l, y, z+h), (x+l, y, z)]
    for v3, v4 in zip(other_vs[:-1], other_vs[1:]):
        # Determine center of tetrahedron.
        center = center_tetrahedron(v1, v2, v3, v4)

        # Decide if the tetrahedron is part of the volume.
        in_volume = decide_in_volume(
            upper_mesh, lower_mesh, center, max_distance, threshold,
            closed_mesh)

        # If the tetrahedron is part of the volume, add it to the primitive
        # list and add its volume to the volume variable.
        if in_volume:
            volume_primitives.append((v1, v2, v3, v4))
            volume += vol_primitive

    return volume


def export_ply_file(points, file_name):
    """Export the center points of the mesh as a pointcloud in a ply file. The
    file is saved in the Downloads folder with the name file_name."""
    np_points = np.asarray(points, dtype=[("x", "f4"), ("y", "f4"),
                                          ("z", "f4"), ("layer", "i4")])
    vertex = PlyElement.describe(np_points, "vertex")
    PlyData([vertex], text=True).write("Downloads/" + file_name)


def space_oriented_volume_between_meshes(
        length, width, height, threshold, minx, maxx, miny, maxy, minz, maxz,
        upper_mesh, lower_mesh, max_distance, primitive, closed_mesh):
    """Calculate the volume and make a 3D model of the volume between 2
    meshes."""
    # Initialize volume primitives list and the volume.
    volume_primitives = []
    cur_volume = 0

    # Determine primitive size
    l, w, h = length, width, height

    # Set volume of the primitive used.
    vol_primitive = set_vol_primitive(l, w, h, primitive)

    # Go over every primitive in bounding box space
    points = make_point_list(minx, maxx, miny, maxy, minz, maxz, l, w, h)

    for x, y, z in points:
        if primitive == "voxel":
            # Check if current voxel is part of the volume.
            cur_volume += process_voxel(
                x, y, z, l, w, h, upper_mesh, lower_mesh, max_distance,
                volume_primitives, vol_primitive, threshold, closed_mesh)
        elif primitive == "tetra":
            # Check which tetrahedra in the current voxel are part of the
            # volume.
            cur_volume += process_tetra(
                x, y, z, l, w, h, upper_mesh, lower_mesh, max_distance,
                volume_primitives, vol_primitive, threshold, closed_mesh)

    return cur_volume, volume_primitives


def space_oriented_algorithm(
        meshes, length, width, height, threshold, minx, maxx, miny, maxy, minz,
        maxz, primitive="voxel", draw=True, test=False, closed_mesh=False,
        export=False, ply_name="pointmesh.ply"):
    """Space-oriented algorithm to make a 3D model out of multiple trianglar
    meshes."""
    # Initialize the total volume and maximum vertical distance.
    points = []
    tot_volume = 0
    max_distance = maxz - minz
    length, width, height = length / 100, width / 100, height / 100
    threshold /= 100

    # For all ordered mesh pairs from top to bottom, run the space-oriented
    # algorithm to get volume and list of primitives.
    for i, (upper_mesh, lower_mesh) in enumerate(zip(meshes[:-1], meshes[1:])):
        # Execute space-oriented algorithm between 2 meshes.
        volume, vol_prims = space_oriented_volume_between_meshes(
            length, width, height, threshold, minx, maxx, miny, maxy, minz,
            maxz, upper_mesh, lower_mesh, max_distance, primitive, closed_mesh)

        # Print the size of the primitives used.
        print_layer_volume(test, volume)

        # Update total volume.
        tot_volume += volume

        # Draw the 3D model based on the type of primitive if it is not a test.
        if draw:
            if primitive == "voxel":
                draw_cubes(vol_prims, length, width, height,
                           RGBAS[lower_mesh % len(RGBAS)])
            elif primitive == "tetra":
                draw_tetrahedra(vol_prims, RGBAS[lower_mesh % len(RGBAS)])
                vol_prims = make_vol_prims_centers(vol_prims)

        if export:
            vol_prims = [(x, y, z, i) for (x, y, z) in vol_prims]
            points.extend(vol_prims)

    if export:
        export_ply_file(points, ply_name)

    return tot_volume


# Start of the object-oriented algortihm.
def find_boundary_vertices(bm):
    """Return all the vertices that are in the boundary of the object."""
    return [v for v in bm.verts if v.is_valid and v.is_boundary]


def find_boundary_edges(bm):
    """Return all the edges that are in the boundary of the object."""
    return [e for e in bm.edges if e.is_valid and e.is_boundary]


def dist_btwn_2d_pts(p1, p2):
    """Calculate the distance between 2 2D points."""
    x_dif, y_dif = p1[0] - p2[0], p1[1] - p2[1]
    return math.sqrt(x_dif**2 + y_dif**2)


def calc_centroid_island(island):
    """Calculate the centroid of a island by taking average values for x, y and
    z coordinates."""
    coordinates = [v.co for v in island]
    centroid = tuple(map(lambda x: sum(x) / float(len(x)), zip(*coordinates)))
    return centroid


def find_closest_island(centroid, cen_list, islands, index):
    """Find element in cen_list that is closest to centroid."""
    # Initiliaze the minimum distance, minimum index in islands list and the
    # minimum center of a island.
    min_dist = math.inf
    min_index = 0
    min_cen = (0, 0, 0)

    # For every center of an island that has not yet been found, calculate its
    # distance in 3D space to the specific island. If this distance is smaller
    # than the current minimum distance, set it to minimum.
    for (i, c) in cen_list:
        dist = dist_btwn_2d_pts(centroid[:2], c[:2])
        if dist < min_dist:
            min_dist = dist
            min_index = i
            min_cen = c

    return min_index, min_cen, min_dist


def find_mesh_pairs(islands):
    """Find pairs of vertex rings that need to be stiched together."""
    # If there are an uneven number of islands, pop the last and thus
    # smallest island.
    if len(islands) % 2 != 0:
        islands.pop()

    # Make a list with tuples of indices and centroids of the islands.
    centroids = []
    for i, isle in enumerate(islands):
        centroids.append((i, calc_centroid_island(isle)))

    # Search for pairs beginning with the largest islands. The pairs are
    # based on centroid distance.
    pairs, found = [], []

    for i, c in centroids:
        if (i, c) not in found:
            not_yet_found = [cen for cen in centroids
                             if cen not in found and cen != (i, c)]
            j, cen, dist = find_closest_island(c, not_yet_found, islands, i)
            if dist > 0.25:
                continue
            else:
                found.append((i, c))
                found.append((j, cen))
                pairs.append([islands[i], islands[j]])

    return pairs


def calculate_closed_triangle_mesh_volume(bm):
    """Calculate the volume of a closed triangle mesh in cubic centimeters."""
    return bm.calc_volume() * 1000000


def check_mesh_closed(bm):
    """Check if the specified mesh is a closed mesh or manifold."""
    return all([v.is_manifold for v in bm.verts])


def remove_loose_parts(bm):
    """Remove loose vertices and edges from the mesh."""
    # Remove faces that are not connected to any other face, e.g. all its
    # edges are boundary edges.
    for f in bm.faces:
        if all([e.is_boundary for e in f.edges]):
            bm.faces.remove(f)

    # Remove vertices that have no face connected to it.
    loose_verts = [v for v in bm.verts if not v.link_faces]
    for v in loose_verts:
        bm.verts.remove(v)

    # Remove edges that have no face conncectd to it.
    loose_edges = [e for e in bm.edges if not e.link_faces]
    for e in loose_edges:
        bm.edges.remove(e)


# This is a function written by batFINGER and can be found here:
# https://blender.stackexchange.com/questions/75332/how-to-find-the-number-of-loose-parts-with-blenders-python-api
def walk_island(vert):
    """Walk all un-tagged linked verts."""
    vert.tag = True
    yield(vert)
    linked_verts = [e.other_vert(vert) for e in vert.link_edges
                    if not e.other_vert(vert).tag and e.is_boundary]

    for v in linked_verts:
        if v.tag:
            continue
        yield from walk_island(v)


# This is a function written by batFINGER and can be found here:
# https://blender.stackexchange.com/questions/75332/how-to-find-the-number-of-loose-parts-with-blenders-python-api
def get_islands(bm, verts=[]):
    """Get islands of vertices given all vertices."""
    def tag(verts, switch):
        for v in verts:
            v.tag = switch
    tag(bm.verts, True)
    tag(verts, False)
    ret = {"islands": []}
    verts = set(verts)
    while verts:
        v = verts.pop()
        verts.add(v)
        island = set(walk_island(v))
        ret["islands"].append(list(island))
        tag(island, False)  # remove tag = True
        verts -= island
    return ret


def make_next_verts(path1, path2, edges, good_verts):
    """Get the next vertices for path1 and path2."""
    # Get the vertices to which the last path vertex is connected to.
    verts1 = [e.other_vert(path1[-1]) for e in edges
              if path1[-1] in e.verts]
    verts2 = [e.other_vert(path2[-1]) for e in edges
              if path2[-1] in e.verts]

    # Get the vertex that is in good_verts and not in the path and is
    # connected to the last path vertex.
    next_vert1 = [v for v in verts1 if v in good_verts and v not in path1]
    next_vert2 = [v for v in verts2 if v in good_verts and v not in path2]

    return next_vert1, next_vert2


def different_paths(path1, path2, next_vert):
    """Check if paths to next_vert are different."""
    route1 = path1[1:]
    end_index = path2.index(next_vert)
    route2 = path2[1:end_index]
    if list(set(route1) & set(route2)):
        return False

    return True


def correct_next_verts(next_vert1, next_vert2, wrong_verts, path1, path2):
    """Returns True if both next_verts are correct."""
    # If the next verts do not not exists or are wrong vertices, they are not
    # correct. Else they are correct.
    if not next_vert1 or not next_vert2:
        return False
    elif next_vert1[0] == path1[0] or next_vert2[0] == path1[0]:
        return False
    elif next_vert1[0] in wrong_verts or next_vert2[0] in wrong_verts:
        return False

    return True


def check_for_overlap(path1, path2):
    """Check if the 2 paths overlap."""
    # The paths overlap if their last vertices are the same or if the last
    # vertex of a path is the same as the second-last of the other path.
    overlap = False
    if path1[-1] == path2[-1]:
        overlap = True
        path1.pop()
    elif path1[-1] == path2[-2] or path2[-1] == path1[-2]:
        overlap = True
        path1.pop()
        path2.pop()

    return overlap


def small_loop_between(start, e1, e2, edges, wrong_verts, good_verts, count):
    """Determines if there exists a small loop between e1 and e2."""
    # Initialize 2 paths from the start vertex with 4 boundary edges connected
    # to it.
    path1 = [start, e1.other_vert(start)] 
    path2 = [start, e2.other_vert(start)]

    # Initialize the loop_found and verts that are in the loop variables.
    loop_found = False
    verts = []

    # Search for a loop while it is not found and count is not less than 0.
    while not loop_found:
        count -= 1
        if count < 0:
            break

        # Get the next vertices in both paths.
        next_vert1, next_vert2 = make_next_verts(path1, path2, edges,
                                                 good_verts)

        # If there is no next vertex or it is a wrong vertex, stop the search.
        if not correct_next_verts(next_vert1, next_vert2, wrong_verts,
                                  path1, path2):
            break

        # Append the next vertices to their paths.
        path1.append(next_vert1[0])
        path2.append(next_vert2[0])

        # Check if a loop is found, e.g. are there overlapping elements in the
        # paths. If so, pop paths accordingly and set loop_found to true.
        loop_found = check_for_overlap(path1, path2)

    # Put all the vertices in the loop in a list, without the start vertex.
    if loop_found:
        verts = path1 + path2
        verts = [v for v in verts if v != start]

    return loop_found, verts


def find_double_loop(start, edges, still_wrong_verts):
    """Find a loop that is between 2 vertices."""
    start_edges = [e for e in edges if start in e.verts]
    paths = []

    # Make all 4 paths from the 4 different edges to a vertex in wrong_verts.
    for e in start_edges:
        found_path = False
        p = [start, e.other_vert(start)]

        while not found_path:
            next_vert = [e.other_vert(p[-1]) for e in edges
                         if p[-1] in e.verts and not p[-2] in e.verts]
            p.append(next_vert[0])
            if p[-1] in still_wrong_verts:
                found_path = True
                paths.append(p)

    # Get the target vertex and the 2 shortest paths toward it.
    path_ends = [p[-1] for p in paths]
    other_v = list(set([v for v in path_ends if path_ends.count(v) > 1]))[0]
    end_edges = [e for e in edges if other_v in e.verts]
    paths_to_other_v = [p for p in paths if p[-1] == other_v]
    paths_to_other_v.sort(key=len)
    shortest_paths = paths_to_other_v[:2]

    # Get loop vertices and loop edges and return them.
    loop_verts = [v for p in shortest_paths for v in p
                  if v not in still_wrong_verts]
    loop_edges = [e for e in start_edges if e.other_vert(start) in loop_verts]
    loop_edges += [e for e in end_edges if e.other_vert(other_v) in loop_verts]
    return loop_verts, loop_edges, other_v    


def remove_loops(mesh, b_edges, edges_to_be_removed, verts_to_be_removed,
                 wrong_verts, combinations, counts):
    """Remove small loops from a vertex island."""
    # Initialize incrementer to 0 and vertices found list to empty.
    i = 0
    verts_found = []

    # While there are vertices with another number than 2 connected edges,
    # try to find and remove the smaller loop on these vertices.
    while len(wrong_verts) > len(verts_found):
        count = counts[i]

        # Loop over wrong vertices where the loop has not yet been found.
        for v in [v for v in wrong_verts if v not in verts_found]:

            # For all edge pair combinations, try to find loop between them.
            edges_list = [e for e in b_edges if v in e.verts]
            for ind1, ind2 in combinations:
                edge1, edge2 = edges_list[ind1], edges_list[ind2]
                loop_found, loop_verts = small_loop_between(
                    v, edge1, edge2, b_edges,
                    [v for v in wrong_verts if v not in verts_found],
                    mesh, count)
                
                # If a loop is found, add edges and vertices in the loop to the
                # to_be_removed lists. Also remove the vertices from the
                # current mesh and add the start vertex to verts_found.
                if loop_found:
                    edges_to_be_removed.extend([edge1, edge2])
                    verts_to_be_removed.extend(loop_verts)
                    for vert in loop_verts:
                        if vert in mesh:
                            mesh.remove(vert)
                    verts_found.append(v)
                    break
        
        # If the incrementer exceeds the length of counts, break. Remaining
        # loops are too big to be found -> increase counts if necessary.
        i += 1
        if i >= len(counts):
            break
    
    # Find double loops if there are still wrong vertices that have not been
    # removed.
    still_wrong_verts = [v for v in wrong_verts if v not in verts_found]
    still_wrong_found = []
    for v in still_wrong_verts:
        if v not in still_wrong_found:
            still_wrong_found.append(v)
            loop_verts, loop_edges, other_v = find_double_loop(
                v, b_edges, still_wrong_verts)
            edges_to_be_removed.extend(loop_edges)
            verts_to_be_removed.extend(loop_verts)
            still_wrong_found.append(other_v)


def remove_small_loops(upper_mesh, lower_mesh, b_edges):
    """Remove small loops from the boundary vertices, e.g. vertices with 4
    edges."""
    # Initialize edges and vertices that need to be removed lists.
    edges_to_be_removed, verts_to_be_removed = [], []

    # Determine all wrong vertices, e.g. vertices with an other number than 2
    # boundary vertices connected to it.
    upper_wrong_verts = [v for v in upper_mesh
                         if len([e for e in b_edges if v in e.verts]) != 2]
    lower_wrong_verts = [v for v in lower_mesh
                         if len([e for e in b_edges if v in e.verts]) != 2]

    # Make combinations of the edges, based on 4 edges.
    combinations = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    
    # Make a count list, so that first the smallest loops are found.
    counts = [2**n for n in range(6)]
    
    # Remove loops in the upper mesh.
    remove_loops(
        upper_mesh, b_edges, edges_to_be_removed, verts_to_be_removed,
        upper_wrong_verts, combinations, counts)
    
    # Remove loops in the lower mesh.
    remove_loops(
        lower_mesh, b_edges, edges_to_be_removed, verts_to_be_removed,
        lower_wrong_verts, combinations, counts)

    return upper_mesh, lower_mesh, edges_to_be_removed, verts_to_be_removed


def sort_vert_list(sorted_list, unsorted, boundary_edges):
    """Create a sorted list of vertices based on edge connections of boundary
    edges."""
    # Add vertices while the length of the sorted list is less than the
    # original list.
    while len(sorted_list) < len(unsorted):
        # Get the last vertex of the list and get the vertices to which this
        # vertex is connected via the connected edges.
        cur_vert = sorted_list[-1]
        edges = [e for e in boundary_edges if cur_vert in e.verts]
        connected = [e.other_vert(cur_vert) for e in edges]
        
        # If the length of the sorted is 1, just add the first connected
        # vertex. Else add the one not yet in the sorted list.
        if len(sorted_list) == 1:
            sorted_list.append(connected[0])
        else:
            next_vert = [v for v in connected if v != sorted_list[-2]]
            sorted_list.extend(next_vert)


def sort_vert_lists(upper_mesh, lower_mesh, b_edges):
    """Sort the lists of BMVerts, so that vertices that are physically next to
    each other, are also next to each other in the list."""
    # Initialize the lists with the vertex at index 0.
    up, low = [upper_mesh[0]], [lower_mesh[0]]
    
    # Sort both island vertices.
    sort_vert_list(up, upper_mesh, b_edges)
    sort_vert_list(low, lower_mesh, b_edges)

    return up, low


def find_long_mesh(mesh1, mesh2):
    """Return longest mesh as first element."""
    if len(mesh1) >= len(mesh2):
        return mesh1, mesh2
    return mesh2, mesh1


def horizontal_edge(vector, rad):
    """Check if the edge is too horinzontal."""
    up = mathutils.Vector((0, 0, 1))
    down = mathutils.Vector((0, 0, -1))
    
    # Edge must be upwards or downwards with an angle <0.6 radians.
    if abs(up.angle(vector)) > rad and abs(down.angle(vector)) > rad:
        return True

    return False


def almost_same_direction(vec1, vec2):
    """Check if vector 1 and vector 2 have almost the same direction."""
    pos_angle = vec2.angle(vec1)
    neg_angle = vec2.angle(-vec1)

    # Direction should not differ more than 25 degrees or 0.45 radians.
    if abs(pos_angle) < 0.45 or abs(neg_angle) < 0.45:
        return True

    return False


def jasnom_step_1_and_2(long_mesh, short_mesh):
    """Execute step 1 and step 2 of the JASNOM algorithm between the long mesh
    and the short mesh."""
    first_edges, second_edges = [], []
    radians = [0.6 + 0.2 * n for n in range(6)]

    # Loop over longest mesh vertices and make edge to closest vertex on the
    # shorter mesh.
    for i, v in enumerate(long_mesh):
        edge_found, hor_edge_found = False, False
        count = 0
        min_dist, min_dist_hor = math.inf, math.inf

        while not edge_found:
            for j, other_v in enumerate(short_mesh): 
                cur_vec = other_v.co - v.co

                cur_dist = dist_btwn_pts(v.co, other_v.co)

                # If the edge is too horizontal dont use it.
                if horizontal_edge(cur_vec, radians[count]):
                    hor_edge_found = True

                    if cur_dist < min_dist_hor:
                        min_dist_hor = cur_dist
                        min_edge_hor = j

                    continue

                # If edge is not close to perpendicular to its base edges, dont use it.
                edge_found = True
                if cur_dist < min_dist:
                    min_dist = cur_dist
                    min_edge = j

            if edge_found:
                if hor_edge_found and (3 * min_dist_hor) < min_dist:
                    min_edge = min_edge_hor
            
            count += 1

        first_edges.append((i, min_edge))

    # Loop in reversed order over longer mesh and make a second edge to the
    # shorter mesh to the target vertex of the previous vertex in the longer
    # mesh.
    for i, v in reversed(first_edges):
        new_index = (i + 1) % len(first_edges)
        second_edges.append((new_index, v))
        
    all_edges = list(set(first_edges + second_edges))
    return all_edges
 

def jasnom_step_3(long_mesh, short_mesh, all_edges):
    """Execute step 3 of the JASNOM algorithm between the long mesh and the
    short mesh."""
    # Check if at least 1 edge connects a vertex of the shorter mesh to the
    # longer mesh. If not, make an edge to the target vertex of a neighbour
    # vertex in the shorter mesh.
    not_connected = [i for i in range(len(short_mesh))
                     if i not in [s for _, s in all_edges]]
    connected_in_this_step = []

    for v_index in not_connected:
        prev_index = ((v_index - 1) % len(short_mesh))
        prev_with_edge = [v1 for (v1, v2) in all_edges if v2 == prev_index]
        while not prev_with_edge:
            prev_index = (prev_index - 1) % len(short_mesh)
            prev_with_edge = [v1 for (v1, v2) in all_edges if v2 == prev_index]

        next_index = ((v_index + 1) % len(short_mesh))
        next_with_edge = [v1 for (v1, v2) in all_edges if v2 == next_index]
        while not next_with_edge:
            next_index = (next_index + 1) % len(short_mesh)
            next_with_edge = [v1 for (v1, v2) in all_edges if v2 == next_index]

        common_vertices = list(set(prev_with_edge) & set(next_with_edge))
        if common_vertices:
            target_vertex = common_vertices[0]
            all_edges.append((target_vertex, v_index))
            connected_in_this_step.append(v_index)
    
    # If there are vertices still not connected, make them into groups which
    # consists of vertices next to each other and add them all to the vertex 
    # in the long mesh closest to the average location.
    still_not_connected = [v for v in not_connected if v not in connected_in_this_step]
    v_index_groups = []
    for v in still_not_connected:
        short_mesh[v].select = True
        added = False
        prev_vert = (v - 1) % len(short_mesh)
        next_vert = (v + 1) % len(short_mesh)

        for group in v_index_groups:
            if prev_vert in group or next_vert in group:
                group.append(v)
                added = True
        
        if not added:
            v_index_groups.append([v])

    v_groups = [[short_mesh[i] for i in indices] for indices in v_index_groups]
    avg_location = [calc_centroid_island(group) for group in v_groups]
   
    for i, loc in enumerate(avg_location):
        min_dist = math.inf

        for j, other_v in enumerate(long_mesh): 
            cur_dist = dist_btwn_pts(loc, other_v.co)
            if cur_dist < min_dist:
                min_dist = cur_dist
                min_edge = j

        for v_index in v_index_groups[i]:
            all_edges.append((min_edge, v_index))


def make_jasnom_faces(long_mesh, short_mesh, new_edges, b_edges):
    """Make faces that are generated by the JASNOM algorithm."""
    new_faces = []
    vertex_pairs = [(e.verts[0], e.verts[1]) for e in b_edges]

    # For all vertices in the long mesh, check if it has multiple edges to the
    # short mesh. If so, make the faces for these edges.
    for v in long_mesh:
        edges_with_v = [e for e in new_edges if v == e[0]]
        if len(edges_with_v) >= 2:
            verts = [e[1] for e in edges_with_v]
            edges = [(v1, v2) for v1, v2 in itertools.combinations(verts, 2)
                     if (v1, v2) in vertex_pairs or (v2, v1) in vertex_pairs]

            for v1, v2 in edges:
                new_faces.append((v, v1, v2))

    # For all vertices in the short mesh, check if it has multiple edges to the
    # long mesh. If so, make the faces for these edges.
    for v in short_mesh:
        edges_with_v = [e for e in new_edges if v == e[1]]
        if len(edges_with_v) >= 2:
            verts = [e[0] for e in edges_with_v]
            edges = [(v1, v2) for v1, v2 in itertools.combinations(verts, 2)
                     if (v1, v2) in vertex_pairs or (v2, v1) in vertex_pairs]

            for v1, v2 in edges:
                new_faces.append((v, v1, v2))
    
    return new_faces


def jasnom_stitch(upper_mesh, lower_mesh, b_edges):
    """Stitch 2 vertex rings together using the JASNOM algorithm. The JASNOM
    algorithm ensures that there are no edges crossing each other."""
    long_mesh, short_mesh = find_long_mesh(upper_mesh, lower_mesh)
    
    all_edges = jasnom_step_1_and_2(long_mesh, short_mesh)
    jasnom_step_3(long_mesh, short_mesh, all_edges)

    # Make lists of edges and faces that need to be added to the mesh.
    new_edges = [(long_mesh[i], short_mesh[j]) for (i, j) in all_edges]
    new_faces = make_jasnom_faces(long_mesh, short_mesh, new_edges, b_edges)

    return new_edges, new_faces


def remove_loops_and_stitch(mesh1, mesh2, b_edges, bmsh, new_edges, new_faces, i):
    """Remove small loops and stitch island pair together."""
    # Remove small loops in the island vertices.
    mesh1, mesh2, edges_removed, verts_removed = remove_small_loops(
        mesh1, mesh2, b_edges)

    # Remove the edges and vertices that are in small loops.
    for e in edges_removed:
        if e.is_valid:
            bmsh.edges.remove(e)
    for v in verts_removed:
        if v.is_valid:
            bmsh.verts.remove(v)

    # Update the boundary edges according to the removal.
    b_edges = [e for e in b_edges if e.is_valid]

    # Sort the vertex islands so that vertices next to each other in the
    # list are also next to each other in the island.
    mesh1, mesh2 = sort_vert_lists(mesh1, mesh2, b_edges)

    # Stitch the 2 islands together using the JASNOM algorithm and add the
    # new edges and faces to the list.
    edge_list, face_list = jasnom_stitch(mesh1, mesh2, b_edges)
    new_edges.extend(edge_list)
    new_faces.extend(face_list)

    return mesh1, mesh2, b_edges


def overlapping_verts(verts, paired):
    """Check if any of the vertices in verts is in a paired island."""
    all_paired_verts = [v for island in paired for v in island]
    return any([v in all_paired_verts for v in verts])


def remove_single_islands(bm, singles, paired):
    """Remove the islands that are not paired with any other island."""
    for i, s in enumerate(singles):
        verts, new_verts = s, s
        new_verts_added = True
        count = 0

        while new_verts_added:
            count += 1
            old_length = len(verts)

            # print("Verts: ", verts)
            # print("New verts: ", new_verts)
            print("Index: %d, depth: %d" % (i, count))

            for v in new_verts:
                if v.is_valid:
                    verts.extend(
                        [e.other_vert(v) for e in v.link_edges if
                         e.other_vert(v) is not None and
                         e.other_vert(v) not in verts])

            new_length = len(verts)
            new_verts_added = new_length > old_length
            new_verts = verts[-(new_length - old_length):]

        if not overlapping_verts(verts, paired):
            for v in verts:
                if v.is_valid:
                    bm.verts.remove(v)


def remove_small_islands(obj):
    """Remove small islands from the mesh."""
    for ob in D.objects:
        ob.select_set(False)

    # Select only the specified object and separate it into loose parts.
    obj.select_set(True)
    bpy.ops.mesh.separate(type="LOOSE")

    # Remove all objects which are too small, <50 vertices.
    for o in C.selected_objects:
        if len(o.data.vertices) < 1000:
            D.meshes.remove(o.data)

    # Join the remaining big objects together.
    C.view_layer.objects.active = C.selected_objects[0]
    bpy.ops.object.join()

    # Remove the mesh data that is not used.
    for m in D.meshes:
        if m.users == 0:
            D.meshes.remove(m)
    
    return C.selected_objects[0]


def fill_in_holes(obj):
    """Fill in the holes of the mesh to get continuous mesh."""
    for ob in D.objects:
        ob.select_set(False)

    # Select only the specified object and fill its holes.
    obj.select_set(True)
    bpy.ops.mesh.fill_holes(sides=3)

    return obj


def make_mesh_manifold(bm):
    """Make the received mesh manifold."""
    # for v in bm.verts:
    #     v.hide = True
    # for e in bm.edges:
    #     e.hide = True
    # for f in bm.faces:
    #     f.hide = True

    # Remove loose edges and vertices.
    remove_loose_parts(bm)

    # Determince boundary vertices and edges.
    b_verts = find_boundary_vertices(bm)
    b_edges = find_boundary_edges(bm)

    # Calculate vertex islands (loose parts) based on the boundary vertices and
    # sort them from large to small.
    islands = [island for island in get_islands(bm, verts=b_verts)["islands"]]
    islands.sort(key=len, reverse=True)

    # island_lengths = [len(isle) for isle in islands]
    # print(island_lengths[:30])
    # Create pairs of island vertices that are close together.
    island_pairs = find_mesh_pairs(islands)
    # paired_islands = [isle for tup in island_pairs for isle in tup if len(isle) < 500]
    # single_islands = [isle for isle in islands if isle not in paired_islands]
    # s_no_doubles = [s for i, s in enumerate(single_islands) if s not in single_islands[:i]]
    # print("There are %d islands and %d single islands!" % (len(islands), len(single_islands)))
    # remove_single_islands(bm, single_islands, paired_islands)

    # TODO: remove islands not in islands_pairs!

    # all_edges_in_pair = [e for e in b_edges if e[0] in pair and e[1] in pair]
    # TODO: try bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=all_edges_in_pair)
    # pair_lengths = [(len(up), len(down)) for [up, down] in island_pairs]
    # print(pair_lengths[:30])

    # for msh in island_pairs[1]:
    #     # v.hide = False
    #     # v.select = True
    #     for v in msh:
    #         v.hide = False
    #         v.select = True
        # for v in low:
        #     v.hide = False
        #     v.select = True

    # Stitch the pairs together using the JASNOM algorithm.
    new_edges, new_faces = [], []
    for i, [upper_mesh, lower_mesh] in enumerate(island_pairs):
        # upper_edges = [e for e in b_edges if e.verts[0] in upper_mesh and e.verts[1] in upper_mesh]
        # lower_edges = [e for e in b_edges if e.verts[0] in lower_mesh and e.verts[1] in lower_mesh]
        # all_edges_in_pair = [e for e in b_edges if e[0] in pair and e[1] in pair]
        # TODO: try bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=all_edges_in_pair)
        # bmesh.ops.bridge_loops(bm, edges=upper_edges + lower_edges, twist_offset=1)
        upper_mesh, lower_mesh, b_edges = remove_loops_and_stitch(
            upper_mesh, lower_mesh, b_edges, bm, new_edges, new_faces, i)

    # bmesh.ops.edgenet_fill(bm, edges=new_edges)
    # Add new edges and faces to the mesh.
    for edge in new_edges:
        if bm.edges.get(edge) is None:
            bm.edges.new(edge)

    for face in new_faces:
        if bm.faces.get(face) is None:
            bm.faces.new(face)

    # remove_single_islands(bm, single_islands, paired_islands)

    # for v in bm.verts:
    #     v.hide = True
    # for e in bm.edges:
    #     e.hide = True
    # for f in bm.faces:
    #     f.hide = True

    # for msh in island_pairs[9]:
    #     for v in msh:
    #         v.hide = False
    #         v.select = False
    # for isle in single_islands:
    #     for v in isle:
    #         v.hide = False
    #         v.select = True

    return bm


def process_objects(obj1, obj2):
    """Combine 2 objects into 1 and remove the 2 objects aftwerwards."""
    volume = 0
    ob1 = remove_small_islands(obj1)
    ob2 = remove_small_islands(obj2)

    # Make a new bmesh that combines data from obj1 and obj2.
    combi = bmesh.new()
    combi.from_mesh(ob1.data)
    combi.from_mesh(ob2.data)

    if check_mesh_closed(combi):
        volume = calculate_closed_triangle_mesh_volume(combi)
    else:
        combi = make_mesh_manifold(combi)

    # Write data to obj1.
    # bmesh.ops.holes_fill(bm, edges=bm.edges, sides=3)
    combi.to_mesh(ob1.data)
    ob1 = remove_small_islands(ob1)

    # ob1 = fill_in_holes(ob1)
    # bpy.ops.mesh.print3d_clean_non_manifold()

    combi.normal_update()
    volume = combi.calc_volume()
    combi.free()

    # Remove obj2 and update view layer.
    D.meshes.remove(ob2.data)
    C.view_layer.update()

    return volume


def update_indices(upper_mesh, lower_mesh, prefix_name):
    """Update the upper- and lower mesh indices, based on the amount of
    triangle mesh volume objects are created."""
    volumes_obj_count = 0
    index = 0

    # Go over all objects.
    for obj in D.objects:
        # If object is a generated volume, increment volume objects counter.
        # Else increment index. If index is the same as upper or lower, set
        # correct index and return them both.
        if obj.name.startswith(prefix_name):
            volumes_obj_count += 1
        else:
            if index == upper_mesh:
                new_up = index + volumes_obj_count

            if index == lower_mesh:
                new_low = index + volumes_obj_count

            index += 1

    return new_up, new_low


def create_object_set_active(mesh_index, prefix_name):
    """Create a new object and set it active in edit mode."""
    # Make a new object which copies data from the object at index mesh_index.
    obj = D.objects[mesh_index].copy()
    obj.data = D.objects[mesh_index].data.copy()
    obj.data.name = prefix_name
    obj.name = prefix_name

    # Give the new_object a new material color.
    new_color = D.materials.new("Layer_color")
    new_color.diffuse_color = RGBAS[mesh_index]
    obj.data.materials[0] = new_color

    # Link the object to the collection and update the view_layer.
    C.collection.objects.link(obj)
    C.view_layer.objects.active = obj
    C.view_layer.update()
    bpy.ops.object.mode_set(mode="EDIT")
    return obj


def delete_verts_and_update(bm, me, del_verts):
    """Delete the vertices specified in the list from the bmesh bm and update
    the mesh me."""
    bmesh.ops.delete(bm, geom=del_verts, context="VERTS")
    bmesh.update_edit_mesh(me)
    bpy.ops.object.mode_set(mode="OBJECT")


def cut_mesh(minx, maxx, miny, maxy, upper_mesh, lower_mesh, threshold,
             max_distance, dr="down"):
    """Remove vertices that are too close to the other mesh."""
    prefix_name = "triangle_mesh_volume"
    del_verts = []
    upper_mesh, lower_mesh = update_indices(upper_mesh, lower_mesh,
                                            prefix_name)

    # Link upper mesh to scene, make it active and set it to edit mode.
    obj = create_object_set_active(upper_mesh, prefix_name)

    # Make a bmesh object from the actice mesh.
    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    # For every vertex in the mesh, add it to the del_vertex list if it is
    # close to other mesh.
    for v in bm.verts:
        if (v.co[0] < minx or v.co[0] > maxx or v.co[1] < miny or
                v.co[1] > maxy):
            del_verts.append(v)
            continue

        if dr == "down":
            ray_shot = D.objects[lower_mesh].ray_cast(v.co, (0, 0, -1),
                                                      distance=max_distance)
        else:
            ray_shot = D.objects[lower_mesh].ray_cast(v.co, (0, 0, 1),
                                                      distance=max_distance)

        if (not ray_shot[0] or
                not dist_btwn_pts(ray_shot[1], v.co) >= threshold):
            del_verts.append(v)

    # Delete all vertices in the del_verts list and update the mesh.
    delete_verts_and_update(bm, me, del_verts)
    bm.free()
    return obj


def object_oriented_algorithm(
        meshes, threshold, minx, maxx, miny, maxy, minz, maxz, test=False):
    """Object-oriented algorithm to make a 3D model out of multiple triangular
    meshes."""
    tot_volume, cur_volume = 0, 0
    max_distance = maxz - minz
    threshold /= 100

    # For all ordered mesh pairs from top to bottom, run the space-oriented
    # algorithm to get volume and list of primitives.
    for upper_mesh, lower_mesh in zip(meshes[:-1], meshes[1:]):
        upper = cut_mesh(minx, maxx, miny, maxy, upper_mesh, lower_mesh,
                         threshold, max_distance, dr="down")
        lower = cut_mesh(minx, maxx, miny, maxy, lower_mesh, upper_mesh,
                         threshold, max_distance, dr="up")
        cur_volume = process_objects(upper, lower)
        print_layer_volume(False, cur_volume)
        tot_volume += cur_volume
        cur_volume = 0

    return tot_volume * 1000000


# The slicer algorithm.
def slicer_algotihm(
        meshes, num_x, num_y, num_z, threshold, minx, maxx, miny, maxy, minz,
        maxz, test=False):
    """A slicer algorithm to make a 3D model out of multiple triangular
    meshes."""
    pass


# The liquid simulation algorithm.
def liquid_simulation_algorithm(
        meshes, num_x, num_y, num_z, threshold, minx, maxx, miny, maxy, minz,
        maxz, test=False):
    """An algorithm that uses liquid simulation to make a 3D model out of
    multiple triangular meshes."""
    pass


# The main part of the code. Change variables and algorithms here.
def main():
    """Execute the script."""
    time_start = time.time()

    selected_meshes = C.selected_objects
    init()

    # Set info about threshold (in cm) for reducing the bounding box.
    threshold = 5

    # Determine bounding box and translate scene to origin.
    minx, maxx, miny, maxy, minz, maxz = bounding_box()
    difx, dify, difz = translate_to_origin(minx, maxx, miny, maxy, minz,
                                           maxz)

    # Update the new minimum and maximum coordinates.
    minx, maxx, miny, maxy, minz, maxz = update_minmax(
        minx, maxx, miny, maxy, minz, maxz, difx, dify, difz)

    method = "space"  # or "space"

    if method == "space":
        # Set number of primitives to divide the bounding box.
        # num_x, num_y, num_z = 150, 150, 50

        # Size in centimeters for the primitives.
        length, width, height = 5, 5, 5
        print_primitive_size(length, width, height)

        export_ply_file = True
        ply_file_name = "pointcloud_meshes.ply"

        # Run the space-oriented algorithm with the assigned primitive.
        primitive = "voxel"  # or "tetra"
        volume = space_oriented_algorithm(
            ordered_meshes(selected_meshes), length, width, height, threshold,
            minx, maxx, miny, maxy, minz, maxz, primitive=primitive,
            export=export_ply_file, ply_name=ply_file_name)
    elif method == "object":
        # Run the object-oriented algorithm.
        volume = object_oriented_algorithm(
            ordered_meshes(selected_meshes), threshold, minx, maxx, miny, maxy,
            minz, maxz)

    print_total_volume(volume)

    print("Script Finished: %.4f sec." % (time.time() - time_start))


if __name__ == "__main__":
    main()
