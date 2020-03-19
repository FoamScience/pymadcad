from mathutils import vec3, mat3, dot, cross, project, noproject, sqrt, acos, spline, interpol1, normalize, distance, length, inverse, transpose, NUMPREC, COMPREC
from mesh import Mesh, Wire, lineedges
import generation as gt
import text
import settings

__all__ = [	'chamfer', 'bevel', 'beveltgt', 
			'tangentjunction', 'cut', 'cutsegments', 'planeoffsets',
			]

# ---- cut methods -----

def cut_width(width, fn1, fn2):
	''' plane offset for a cut based on the width of the bevel '''
	n = normalize(fn1+fn2)
	s = dot(fn1,n)
	return -width/2 * sqrt(1/s**2 - 1) * n

def cut_distance(depth, fn1, fn2):
	''' plane offset for a cut based on the distance along the side faces '''
	return -depth * normalize(fn1+fn2)

def cut_depth(dist, fn1, fn2):
	''' plane offset for a cut based on the distance to the cutted edge '''
	return -dist * cross(normalize(cross(fn1,fn2)), fn1-fn2)

def cut_angle(depth, fn1, fn2):
	''' plane offset for a cut based on the angle between faces '''
	s = dot(fn1,n)
	return -depth/2 * (1/s - s) * n

# ----- user functions ------

def chamfer(mesh, line, cutter):
	''' create a chamfer on the given suite of points, create faces are planes.
		cutter is described in function planeoffsets()
	'''
	# cut faces
	segments = cut(mesh, line, planeoffsets(mesh, line, cutter))
	
	# create junctions
	group = len(mesh.groups)
	mesh.groups.append('junction')
	for i,s in enumerate(segments):
		if s:
			lp = []
			for part in gt.makeloops(s):
				lp.extend(part)
			gt.triangulate(mesh, lp, group)

def bevel3(mesh, line, cutter, interpol=spline, resolution=None):
	''' create a round profile on the given suite of points, create faces form cylindric surfaces.
		cutter is described in function planeoffsets()
	'''
	# cut faces
	conn = connectivity_edgeface(mesh.faces)
	segments = cut(mesh, line, planeoffsets(mesh, line, cutter), conn)
	conn = connectivity_edgeface(mesh.faces)
	
	parts = []
	for s in segments:
		parts.extend(gt.makeloops(s))
	left,right = gt.makeloops(parts)
	right.reverse()
	match = list(gt.matchcurves((mesh.points, left), (mesh.points, right)))
	
	# create parameters for the round profiles
	params = []
	for i in range(len(match)-1):
		dir =	( mesh.points[match[i+1][0]] - mesh.points[match[i][0]]
				+ mesh.points[match[i+1][1]] - mesh.points[match[i][1]] )
		e = (match[i+1][0], match[i][0])
		if e in conn:	tl = normalize(cross(mesh.facenormal(conn[e]), dir))
		else:			tl = vec3(0)
		e = (match[i][1], match[i+1][1])
		if e in conn:	tr = -normalize(cross(mesh.facenormal(conn[e]), dir))
		else:			tr = vec3(0)
		params.append((dir, tl, tr))
	
	params.append((params[-1][0], normalize(params[-1][1]), normalize(params[-1][2])))
	for i in range(1, len(params)-1):
		params[i] = (
				0.5*(params[i][0] + params[i-1][0]),
				normalize(params[i][1] + params[i-1][1]),
				normalize(params[i][2] + params[i-1][2]),
				)
	
	# determine the number of segments
	segts = 0
	for (l,r),(dir,tl,tr) in zip(match, params):
		angle = min(1, acos(dot(tl,tr)))
		dist = length(mesh.points[match[i][1]]-mesh.points[match[i][0]])
		div = settings.curve_resolution(dist, angle, resolution)+2
		if div > segts:
			segts = div
	
	# create points
	startpt = len(mesh.points)
	for (l,r),(dir,tl,tr) in zip(match, params):
		link = mesh.points[l]-mesh.points[r]
		nlink = length(link)
		link /= nlink
		
		for j in range(segts):
			x = j/(segts-1)
			mesh.points.append(spline(
				(mesh.points[l], nlink*tl),
				(mesh.points[r], nlink*tr),
				x))
	# create faces
	group = len(mesh.groups)
	mesh.groups.append('junction')
	for i in range(len(match)-1):
		for j in range(segts-1):
			s = startpt+i*segts+j
			mesh.faces.append((s,         s+segts, s+1))
			mesh.faces.append((s+1+segts,   s+1,   s+segts))
			mesh.tracks.append(group)
			mesh.tracks.append(group)
				
def beveltgt(mesh, line, cutter, interpol=spline, resolution=None):
	''' create a round profile on the given suite of points, create faces form cylindric surfaces.
		tangents to cuted faces will be used for interpolation
		cutter is described in function planeoffsets()
		
		WARNING: the tangency to cuted faces can lead to weired geometries in case of concave shape
	'''
	# cut faces
	conn = connectivity_edgeface(mesh.faces)
	segments = cut(mesh, line, planeoffsets(mesh, line, cutter), conn)
	conn = connectivity_edgeface(mesh.faces)
	group = Mesh(groups=['junction'])
	tangents = {}
	tmatch = []
	
	for (a,b),s in zip(lineedges(line), segments):
		if not s:	continue
		
		dir = mesh.points[a] - mesh.points[b]
		
		lps = gt.makeloops(s)
		if len(lps) == 1:
			gt.triangulate(mesh, lp, group)
		else:
			left,right = lps
			if dot(dir, mesh.points[left[1]] - mesh.points[left[0]]) > 0:
				left,right = right,left
			right.reverse()
			ll, lr = Wire(mesh.points, left).length(), Wire(mesh.points, right).length()
			match = list(gt.curvematch(Wire(mesh.points, left), Wire(mesh.points, right)))
			tmatch.extend(match)
			
			# create parameters for the round profiles
			x = 0
			for i in range(len(match)-1):
				e = (match[i+1][0], match[i][0])
				if e in conn:	tl = mesh.facenormal(conn[e])
				else:			tl = None
				e = (match[i][1], match[i+1][1])
				if e in conn:	tr = mesh.facenormal(conn[e])
				else:			tr = None
				x += distance(mesh.points[match[i+1][0]], mesh.points[match[i][0]]) / ll
				
				for j in (0,1):
					l,r = match[i+j]
					o = interpol1(mesh.points[a], mesh.points[b], x)
					plane = normalize(cross(mesh.points[r]-o, mesh.points[l]-o))
					if tl:	tangents[l] = normalize(cross(plane, tl)) + tangents.get(l, 0)
					if tr:	tangents[r] = normalize(cross(tr, plane)) + tangents.get(r, 0)
	
	mesh += tangentjunction(mesh.points, tmatch, tangents, resolution, interpol)
			
def bevel(mesh, line, cutter, interpol=spline, resolution=None):
	''' create a smooth interpolated profile at the given suite of points
		tangents to line's adjacents faces will be used for interpolation
		cutter is described in function planeoffsets()
		
		WARNING: to use tangents from line adjacents faces can lead to matter add in case of concave shape
	'''
	# cut faces
	conn = connectivity_edgeface(mesh.faces)
	normals = []
	for e in lineedges(line):
		normals.append((
			mesh.facenormal(conn[(e[1],e[0])]),
			mesh.facenormal(conn[e]),
			))
	
	segments = cut(mesh, line, planeoffsets(mesh, line, cutter), conn)
	tangents = {}
	tmatch = []
	
	for (a,b),s,(nl,nr) in zip(lineedges(line), segments, normals):
		if not s:	continue
		
		lps = gt.makeloops(s)
		if len(lps) == 1:
			gt.triangulate(mesh, lp, group)
		else:
			left,right = lps
			if dot(mesh.points[a] - mesh.points[b], mesh.points[left[1]] - mesh.points[left[0]]) > 0:
				left,right = right,left
			right.reverse()
			ll, lr = Wire(mesh.points, left).length(), Wire(mesh.points, right).length()
			match = list(gt.curvematch(Wire(mesh.points, left), 
									   Wire(mesh.points, right) ))
			tmatch.extend(match)
			
			# create parameters for the round profiles
			x = 0
			for i in range(len(match)-1):
				x += distance(mesh.points[match[i+1][0]], mesh.points[match[i][0]]) / ll
				
				for j in (0,1):
					l,r = match[i+j]
					o = interpol1(mesh.points[a], mesh.points[b], x)
					plane = normalize(cross(mesh.points[r]-o, mesh.points[l]-o))
					tangents[l] = normalize(cross(plane, nl)) + tangents.get(l, 0)
					tangents[r] = normalize(cross(nr, plane)) + tangents.get(r, 0)
	
	mesh += tangentjunction(mesh.points, tmatch, tangents, resolution, interpol)

def tangentjunction(points, match, tangents, resolution=None, interpol=spline):
	''' create a surface between interpolated curves for each match '''
	group = Mesh(groups=['junction'])
	# determine the number of segments
	div = 0
	for l,r in match:
		dist = distance(points[l], points[r])
		tangents[l] = tl = normalize(tangents[l]) * dist
		tangents[r] = tr = normalize(tangents[r]) * dist
		angle = min(1, acos(dot(tl,tr)))
		dist = length(points[l]-points[r])
		ldiv = settings.curve_resolution(dist, angle, resolution)
		if ldiv > div:
			div = ldiv
	
	return gt.junctioniter(
			( ((points[r], tangents[r]), (points[l], tangents[l])) for l,r in match),
			div, interpol)

# ----- algorithm ------

def planeoffsets(mesh, line, cutter):
	''' compute the offsets for cutting planes using the given method 
		cutter is a tuple or a function
		
			- function(fn1,fn2) -> offset 		
				fn1, fn2 are the adjacents face normals
				offset is the distance from segment to plane times the normal to the plane
				
			- ('method', distance) 				
				the method is the string name of the method (a function named 'cut_'+method existing in this module)
				distance depends on the method and is the numeric parameter of the method
	'''
	cutter = interpretcutter(cutter)
	
	# get adjacent faces' normals to lines
	adjacents = ({}, {})	# (left adjacents, right adjacents)
	segts = segmentsdict(line)
	for f in mesh.faces:
		for e in ((f[0],f[1]), (f[1],f[2]), (f[2],f[0])):
			if e in segts:					adjacents[0][segts[e]] = mesh.facenormal(f)
			elif (e[1],e[0]) in segts:		adjacents[1][segts[(e[1],e[0])]] = mesh.facenormal(f)
	
	# compute offsets (displacement on depth)
	offsets = []
	for i in range(len(line)-1):
		fn1,fn2 = adjacents[0][i], adjacents[1][i]
		offset = cutter(fn1, fn2)		
		if dot(cross(fn1, fn2), mesh.points[line[i+1]]-mesh.points[line[i]]) < 0:
			offset = -offset
		offsets.append(offset)
	
	return offsets

def interpretcutter(cutter):
	if isinstance(cutter, tuple):
		func = globals()['cut_'+cutter[0]]
		arg = cutter[1]
		return lambda fn1,fn2: func(arg, fn1, fn2)
	elif callable(cutter):
		return cutter
	else:
		raise TypeError("cutter must be a callable or a tuple (name, param)")

def cutsegments(mesh, line, offsets):
	# compute cut planes and their intersections
	#grp = len(mesh.groups)
	#mesh.groups.append(None)
	segments = []	# planes intersections  (origin, plane normal, axis direction)
	for i in range(1,len(line)-1):
		n1, n2 = offsets[i-1], offsets[i]
		d = cross(n1, n2)
		if length(d) > NUMPREC:
			d = normalize(d)
			p = mesh.points[line[i]]
			intersect = inverse(transpose(mat3(n1, n2, d))) * vec3(
							dot(p+n1, n1), 
							dot(p+n2, n2), 
							dot(p, d))
			n = normalize(cross(d, intersect-p))
			if dot(n, mesh.points[line[i]]-mesh.points[line[i-1]]) > 0:		n = -n
			segments.append((intersect, n, d))
		else:
			segments.append(None)
		
		#l = len(mesh.points)
		#d = normalize(d)
		#mesh.points.append(p)
		#mesh.points.append(intersect+d)
		#mesh.points.append(intersect-d)
		#mesh.faces.append((l,l+1,l+2))
		#mesh.tracks.append(grp)
	return segments

def cut(mesh, line, offsets, conn=None):
	toremove = set()		# faces to remove that match no replacements
	result = []				# intersection segments for each offset

	# build connectivity
	if not conn:
		conn = connectivity_edgeface(mesh.faces)
	# segments planes and normals
	segments = cutsegments(mesh, line, offsets)
	
	# complete segments that cannot be computed locally (straight suite of points for example)
	for i in range(1,len(segments)):
		if i and not segments[i]:		segments[i] = segments[i-1]
	for i in reversed(range(len(segments)-1)):
		if i and not segments[i]:		segments[i] = segments[i+1]
	
	# cut at each plane
	for i in range(1,len(line)):
		# propagate until cut
		cutplane = (mesh.points[line[i-1]]+offsets[i-1], -normalize(offsets[i-1]))
		#print('cutplane', cutplane)
		s1 = segments[i-2] if i >= 2 else None
		s2 = segments[i-1] if i <= len(segments) else None
		seen = set()
		front = [(line[i],line[i-1]), (line[i-1],line[i])]
		intersections = set()
		while front:
			frontedge = front.pop()
			if frontedge not in conn:	continue
			fi = conn[frontedge]
			if fi in seen:	continue
			
			f = mesh.faces[fi]
			#print(fi, 'for', frontedge)
			# find the intersection of the triangle with the common axis to the two cutplanes (current and next)
			p = intersection_axis_face((s2[0], s2[2]), mesh.facepoints(fi)) if s2 else None
			if p and distance(p, mesh.points[f[0]]) > NUMPREC and distance(p, mesh.points[f[1]]) > NUMPREC and distance(p, mesh.points[f[2]]) > NUMPREC:
				# mark cutplane change
				unregisterface(mesh, conn, fi)
				pi = insertpoint(mesh, p)
				l = len(mesh.faces)
				mesh.faces[fi] = (f[0], f[1], pi)
				mesh.faces.append((f[1], f[2], pi))
				mesh.faces.append((f[2], f[0], pi))
				mesh.tracks.append(mesh.tracks[fi])
				mesh.tracks.append(mesh.tracks[fi])
				registerface(mesh, conn, fi)
				registerface(mesh, conn, l)
				registerface(mesh, conn, l+1)
				front.append(frontedge)
			else:
				# mark this face as processed
				seen.add(fi)
				
				#scn3D.add(text.Text(
					#(mesh.points[f[0]] + mesh.points[f[1]] + mesh.points[f[2]]) /3,
					#'  '+str(fi),
					#8,
					#color=(0.1, 1, 0.4),
					#align=('left', 'center'),
					#))
				
				# point side for propagation
				goodside = [False]*3
				for j,pi in enumerate(f):
					#goodside[j] = 	dot(mesh.points[pi]-cutplane[0], cutplane[1]) > NUMPREC 
					goodside[j] = 	dot(mesh.points[pi]-cutplane[0], cutplane[1]) > -NUMPREC
				goodx = [False]*3
				for j,pi in enumerate(f):
					p = mesh.points[pi]
					goodx[j] = ( (not s1 or dot(p-s1[0], -s1[1]) >= 0)
							 and (not s2 or dot(p-s2[0],  s2[1]) >= 0) )
				
				if goodside[0] or goodside[1] or goodside[2]:
					for j in range(3):
						front.append((f[j],f[j-1]))
				else:
					continue
				
				# intersections of triangle's edges with the plane
				cut = [None]*3
				for j,e in enumerate(((f[0],f[1]), (f[1],f[2]), (f[2],f[0]))):
					cut[j] = intersection_edge_plane(cutplane, (mesh.points[e[0]], mesh.points[e[1]]))
				for j in range(3):
					if cut[j-1] and cut[j] and distance(cut[j-1], cut[j]) < NUMPREC:	cut[j] = None
				
				if goodside[0] and goodside[1] and goodside[2] and (goodx[0] or goodx[1] or goodx[2]):
					toremove.add(fi)
				
				# cut the face
				cutted = False
				for j in range(3):
					if cut[j] and cut[j-1]:
						cutted = True
						# cut only if the intersection segment is in the delimited area
						if s1 and dot(cut[j-1]-s1[0],-s1[1]) < NUMPREC and dot(cut[j]-s1[0],-s1[1]) < NUMPREC:	continue
						if s2 and dot(cut[j-1]-s2[0], s2[1]) < NUMPREC and dot(cut[j]-s2[0], s2[1]) < NUMPREC:	continue
						
						# cut the face (create face even for non kept side, necessary for propagation)
						toremove.discard(fi)
						f = mesh.faces[fi]
						p1 = insertpoint(mesh, cut[j])
						p2 = insertpoint(mesh, cut[j-1])
						unregisterface(mesh, conn, fi)
						l = len(mesh.faces)
						mesh.faces[fi] = (p1, f[j-2], f[j-1])
						mesh.faces.append((p1, f[j-1], p2))
						mesh.faces.append((p1, p2, f[j-0]))
						mesh.tracks.append(mesh.tracks[fi])
						mesh.tracks.append(mesh.tracks[fi])
						registerface(mesh, conn, fi)
						registerface(mesh, conn, l)
						registerface(mesh, conn, l+1)
						seen.update((fi, l, l+1))
						# remove the faces outside
						if dot(mesh.points[f[j]]-cutplane[0], cutplane[1]) < 0:
							toremove.add(fi)
							toremove.add(l)
							intersections.add((p2,p1))
						else:
							toremove.add(l+1)
							intersections.add((p1,p2))
						break
		result.append(intersections)
	# delete inside faces and empty ones
	removefaces(mesh, lambda fi: fi in toremove or facesurf(mesh,fi) < NUMPREC)
	
	return result


def insertpoint(mesh, pt):
	return mesh.usepointat(pt)

def connectivity_edgeface(faces):
	conn = {}
	for i,f in enumerate(faces):
		for e in ((f[0],f[1]), (f[1],f[2]), (f[2],f[0])):
			conn[e] = i
	return conn

def registerface(mesh, conn, fi):
	f = mesh.faces[fi]
	for e in ((f[0],f[1]), (f[1],f[2]), (f[2],f[0])):
		conn[e] = fi
		
def unregisterface(mesh, conn, fi):
	f = mesh.faces[fi]
	for e in ((f[0],f[1]), (f[1],f[2]), (f[2],f[0])):
		if e in conn:	del conn[e]

def segmentsdict(line):
	segments = {}
	for i in range(len(line)-1):
		segments[(line[i],line[i+1])] = i
	return segments

# return intersection of an edge with a plane, or None
def intersection_edge_plane(axis, edge):
	dist = dot(axis[0]-edge[0], axis[1])
	compl = dot(axis[0]-edge[1], axis[1])
	if abs(dist) < NUMPREC:		return edge[0]
	if abs(compl) < NUMPREC:	return edge[1]
	if dist * compl > 0:	return None		# the segment doesn't reach the plane
	edgedir = edge[1]-edge[0]
	if abs(dot(edgedir, axis[1])) < NUMPREC:	return None	# the segment is parallel to the plane
	edgedir = normalize(edgedir)
	return edge[0] + dist * edgedir / dot(edgedir, axis[1])


def intersection_axis_face(axis, face):
	coords = inverse(mat3(face[1]-face[0], face[2]-face[0], axis[1])) * (axis[0] - face[0])
	if 0 <= coords[0] and 0 <= coords[1] and coords[0]+coords[1] <= 1 :
		return axis[0] - axis[1]*coords[2]
	else:
		return None


def removefaces(mesh, crit):
	''' remove faces whose indices are present in faces, (for huge amount, prefer pass faces as a set) '''
	newfaces = []
	newtracks = []
	for i in range(len(mesh.faces)):
		if not crit(i):
			newfaces.append(mesh.faces[i])
			newtracks.append(mesh.tracks[i])
	mesh.faces = newfaces
	mesh.tracks = newtracks

def facesurf(mesh, fi):
	o,x,y = mesh.facepoints(fi)
	return length(cross(x-o, y-o))


if __name__ == '__main__':
	
	# test intersections
	from generation import saddle, tube, makeloops
	from primitives import Arc
	from mesh import Web, web
	import sys
	import view, text
	from PyQt5.QtWidgets import QApplication
	from nprint import nprint
	from copy import deepcopy
	
	app = QApplication(sys.argv)
	main = scn3D = view.Scene()
	
	m = saddle(
			Web(
				[vec3(-2,1.5,0),vec3(-1,1,0),vec3(0,0,0),vec3(1,1,0),vec3(1.5,2,0)], 
				[(0,1), (1,2), (2,3), (3,4)],
				[0,1,2,3]),
			#web(vec3(0,1,-1),vec3(0,0,0),vec3(0,1,1)),
			#web(Arc(vec3(0,1,-1),vec3(0,1.5,0),vec3(0,1,1))),
			web(
				Arc(vec3(0,1,-1),vec3(0,1.3,-0.5),vec3(0,1,0)), 
				Arc(vec3(0,1,0),vec3(0,0.7,0.5),vec3(0,1,1))),
			)
	m.check()
	
	line = makeloops(list(m.group(1).outlines_unoriented() & m.group(2).outlines_unoriented()))[0]
	#chamfer(m, line, ('depth', 0.6))
	#bevel3(m, line, ('depth', 0.2))
	#beveltgt(m, line, ('depth', 0.6))
	bevel(m, line, ('depth', 0.6))
	
	
	#m.options.update({'debug_display': True, 'debug_points': False })
	scn3D.add(m)
	scn3D.look(m.box())
	main.show()
	sys.exit(app.exec())
