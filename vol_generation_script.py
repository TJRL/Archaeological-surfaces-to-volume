# This is a script made to calculate the volume between different surfaces
# of archaeological excavation grounds. It implements different methods to do
# so. The surfaces are triangle meshes.
#
# Made by Bram Dekker (11428279) of the Univeristy of Amsterdam as a bachelor
# thesis.

import bpy
import bmesh
import time
import math
import numpy as np

C = bpy.context
D = bpy.data

RED = (1, 0, 0, 1)
GREEN = (0, 1, 0, 1)
BLUE = (0, 0, 1, 1)
GREY = (0.5, 0.5, 0.5, 1)
BLACK = (0, 0, 0, 1)
WHITE = (1, 1, 1, 1)
RGBAS = [RED, GREEN, BLUE, BLACK, WHITE, GREY]


def init(test=False):
    """Initialize the scene by removing the cube, camera and light and import
    and orientate the trench objects."""
    if test:
        clear_scene()
    else:
        remove_volumes()
        rotate_objects()


def remove_volumes():
    """Remove the generated volumes from the last script run."""
    for m in D.meshes:
        if m.name.startswith("cubic") or m.name.startswith("tetra"):
            D.meshes.remove(m)


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
    print("Primitive size: %.2f x %.2f x %.2f" % (length, width, height))


def print_layer_volume(test, volume):
    """Print the layer volume only if it is not a test run."""
    if not test:
        print("This layer has a volume of %.2f cm3 or %.2f m3" %
              (volume, volume / 1000000))


def ordered_meshes():
    """Return the list of indices in de bpy.data.objects list of all
    objects from high to low (highest avg z-coordinate of vertices)."""
    mesh_list = []

    for i, obj in enumerate(D.objects):
        cur_avg = np.average([vt.co[2] for vt in obj.data.vertices.values()])
        mesh_list.append((cur_avg, i))

    return [elem[1] for elem in sorted(mesh_list, reverse=True)]


def dist_btwn_pts(p1, p2):
    """Calculate the distance between 2 points in 3D space"""
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

    # TODO: check if vertex already in list. If so get its index and give it
    # to make_faces function --> Is slower!!!
    for vs in vertices:
        # i1, i2, i3, i4 = check_tetra_indices(verts, v1, v2, v3, v4)
        verts.extend(vs)
        # add_tetra_faces(faces, i1, i2, i3, i4)
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


def set_vol_primitive(length, width, height, primitive="voxel"):
    """Calculate the volume of the specified primitive in cubic centimetres."""
    if primitive == "voxel":
        vol_primitive = length * width * height * 1000000
    elif primitive == "tetra":
        vol_primitive = 1000000 * (length * width * height) / 6

    return vol_primitive


def decide_in_volume(upper_mesh, lower_mesh, center, max_distance, threshold):
    """Decide if the primitive on the given position belongs to the volume
    between the meshes."""
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


def process_voxel(x, y, z, l, w, h, upper_mesh, lower_mesh, max_distance,
                  volume_primitives, vol_primitive, threshold):
    """Determine if voxel is part of the volume or not."""
    # Initialize volume to zero.
    volume = 0

    # Determine center of voxel.
    center = (x+l/2, y+w/2, z+h/2)

    # Decide if voxel is part of the volume.
    in_volume = decide_in_volume(upper_mesh, lower_mesh, center, max_distance,
                                 threshold)

    # If the voxel is part of the volume, add it to the primitive list and set
    # the volume.
    if in_volume:
        volume_primitives.append((x, y, z))
        volume = vol_primitive

    return volume


def process_tetra(x, y, z, l, w, h, upper_mesh, lower_mesh, max_distance,
                  volume_primitives, vol_primitive, threshold):
    """Determine if tetra is part of the volume or not."""
    # Initialize volume to zero.
    volume = 0

    # Get all vertices for the 6 tetrahedra.
    v1, v2 = (x, y, z), (x + l, y + w, z + h)
    other_vs = [(x+l, y, z), (x+l, y+w, z), (x, y+w, z), (x, y+w, z+h),
                (x, y, z+h), (x+l, y, z+h), (x+l, y, z)]
    for v3, v4 in zip(other_vs[:-1], other_vs[1:]):
        # Determine center of tetrahedron.
        center = center_tetrahedron(v1, v2, v3, v4)

        # Decide if the tetrahedron is part of the volume.
        in_volume = decide_in_volume(upper_mesh, lower_mesh, center,
                                     max_distance, threshold)

        # If the tetrahedron is part of the volume, add it to the primitive
        # list and add its volume to the volume variable.
        if in_volume:
            volume_primitives.append((v1, v2, v3, v4))
            volume += vol_primitive

    return volume


def space_oriented_volume_between_meshes(
        length, width, height, threshold, minx, maxx, miny, maxy, minz, maxz,
        upper_mesh, lower_mesh, max_distance,  primitive="voxel"):
    """Calculate the volume and make a 3D model of the volume between 2
    meshes."""
    # Initialize volume primitives list and the volume.
    volume_primitives = []
    cur_volume = 0

    # Determine primitive size
    l, w, h = length, width, height

    # Set volume of the primitive used.
    vol_primitive = set_vol_primitive(l, w, h, primitive=primitive)

    # Go over every primitive in bounding box space
    points = make_point_list(minx, maxx, miny, maxy, minz, maxz, l, w, h)

    for x, y, z in points:
        if primitive == "voxel":
            # Check if current voxel is part of the volume.
            cur_volume += process_voxel(
                x, y, z, l, w, h, upper_mesh, lower_mesh, max_distance,
                volume_primitives, vol_primitive, threshold)
        elif primitive == "tetra":
            # Check which tetrahedra in the current voxel are part of the
            # volume.
            cur_volume += process_tetra(
                x, y, z, l, w, h, upper_mesh, lower_mesh, max_distance,
                volume_primitives, vol_primitive, threshold)

    return cur_volume, volume_primitives


def space_oriented_algorithm(
        meshes, length, width, height, threshold, minx, maxx, miny, maxy, minz,
        maxz, primitive="voxel", draw=True, test=False):
    """Space-oriented algorithm to make a 3D model out of multiple trianglar
    meshes."""
    # Initialize the total volume and maximum vertical distance.
    tot_volume = 0
    max_distance = maxz - minz

    # For all ordered mesh pairs from top to bottom, run the space-oriented
    # algorithm to get volume and list of primitives.
    for upper_mesh, lower_mesh in zip(meshes[:-1], meshes[1:]):
        # Execute space-oriented algorithm between 2 meshes.
        volume, vol_prims = space_oriented_volume_between_meshes(
            length, width, height, threshold, minx, maxx, miny, maxy, minz,
            maxz, upper_mesh, lower_mesh, max_distance, primitive=primitive)

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

    return tot_volume


def cut_mesh(minx, maxx, miny, maxy, upper_mesh, lower_mesh, threshold,
             max_distance, dr="down"):
    """Remove vertices that are too close to the other mesh."""
    del_verts = []

    # Link upper mesh to scene, make it active and set it to edit mode.
    obj = D.objects[upper_mesh]
    # C.scene.collection.objects.link(obj)
    C.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")

    # Make a bmesh object from the actice mesh.
    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    # For every vertex in the mesh, add it to the del_vertex list if it is
    # close to other mesh.
    for v in bm.verts:
        if (v.co[0] < minx or v.co[0] > maxx or v.co[1] < miny or
                v.co[1] > maxy):
            # b_count += 1
            del_verts.append(v)
            continue

        if dr == "down":
            ray_shot = D.objects[lower_mesh].ray_cast(v.co, (0, 0, -1),
                                                      distance=max_distance)
        else:
            ray_shot = D.objects[lower_mesh].ray_cast(v.co, (0, 0, 1),
                                                      distance=max_distance)

        if ray_shot[0] and dist_btwn_pts(ray_shot[1], v.co) >= threshold:
            continue
            # g_count += 1
            # print("This is a good vertex!")
        else:
            # b_count += 1
            del_verts.append(v)
            # print("This is a bad vertex!")

    # Delete all vertices in the del_verts list and update the mesh.
    bmesh.ops.delete(bm, geom=del_verts, context="VERTS")
    bmesh.update_edit_mesh(me)
    bpy.ops.object.mode_set(mode="OBJECT")


def object_oriented_algorithm(
        meshes, num_x, num_y, num_z, threshold, minx, maxx, miny, maxy, minz,
        maxz, test=False):
    """Object-oriented algorithm to make a 3D model out of multiple triangular
    meshes."""
    tot_volume = 0
    max_distance = maxz - minz

    # For all ordered mesh pairs from top to bottom, run the space-oriented
    # algorithm to get volume and list of primitives.
    for upper_mesh, lower_mesh in zip(meshes[:-1], meshes[1:]):
        minx, maxx, miny, maxy = reduce_boundingbox(
            upper_mesh, lower_mesh, threshold, minx, maxx, miny, maxy, maxz)

        cut_mesh(minx, maxx, miny, maxy, upper_mesh, lower_mesh, threshold,
                 max_distance, dr="down")
        cut_mesh(minx, maxx, miny, maxy, lower_mesh, upper_mesh, threshold,
                 max_distance, dr="up")

    # print("There are %d good vertices and %d bad vertices!" %
        #   (g_count, b_count))
    return tot_volume


def slicer_algotihm(
        meshes, num_x, num_y, num_z, threshold, minx, maxx, miny, maxy, minz,
        maxz, test=False):
    """A slicer algorithm to make a 3D model out of multiple triangular
    meshes."""
    pass


def liquid_simulation_algorithm(
        meshes, num_x, num_y, num_z, threshold, minx, maxx, miny, maxy, minz,
        maxz, test=False):
    """An algorithm that uses liquid simulation to make a 3D model out of
    multiple triangular meshes."""
    pass


def main():
    """Execute the script."""
    time_start = time.time()

    init()

    # Set info about threshold (in m) for reducing the bounding box.
    threshold = 0.05

    # Set number of primitives to divide the bounding box.
    # num_x, num_y, num_z = 150, 150, 50

    # Size in meters for the primitives.
    length, width, height = 0.05, 0.05, 0.05
    print_primitive_size(length, width, height)
    # TODO: sizes instead of amount of primitives.
    # print_num_primitives(num_x, num_y, num_z)

    # Determine bounding box and translate scene to origin.
    minx, maxx, miny, maxy, minz, maxz = bounding_box()
    difx, dify, difz = translate_to_origin(minx, maxx, miny, maxy, minz,
                                           maxz)

    # Update the new minimum and maximum coordinates.
    minx, maxx, miny, maxy, minz, maxz = update_minmax(
        minx, maxx, miny, maxy, minz, maxz, difx, dify, difz)

    print_bbox(minx, maxx, miny, maxy, minz, maxz)

    # volume = object_oriented_algorithm(
    #     ordered_meshes(), num_x, num_y, num_z, threshold, minx, maxx, miny,
    #     maxy, minz, maxz)
    # # Run the space-oriented algorithm with the assigned primitive.
    primitive = "voxel"
    volume = space_oriented_algorithm(
        ordered_meshes(), length, width, height, threshold, minx, maxx, miny,
        maxy, minz, maxz, primitive=primitive)

    print_total_volume(volume)

    print("Script Finished: %.4f sec" % (time.time() - time_start))


if __name__ == "__main__":
    main()
