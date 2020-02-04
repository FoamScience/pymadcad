''' Regroupement des fonctions et classes math de pymadcad '''

import glm
from glm import *
from math import pi

'''
vec3 = dvec3
mat3 = dmat3
vec4 = dvec4
mat4 = dmat4

NUMPREC = 1e-12
'''

# numerical precision of floats used (float32 here, so 7 decimals, so 1e-6 when exponent is 1)
NUMPREC = 1e-6
COMPREC = 1-NUMPREC


def anglebt(x,y):
	n = length(x)*length(y)
	return acos(dot(x,y) / n)	if n else 0

def project(vec, dir):
	return dot(vec, dir) * dir

def perpdot(a:vec2, b:vec2) -> float:
	return -a[1]*b[0] + a[0]*b[1]

# donne la matrice de transformation 4x4
def transform(translation=None, rotation=None):
	if rotation is not None:	transform = mat4(rotation)
	else:						transform = mat4(1)
	if translation is not None:	transform[3] = vec4(translation)
	return transform

# donne la matrice de transformation 4x4 inverse
def inversetransform(transform):
	if isinstance(transform, tuple):		return (-transform[0], inversetransform(transform[1]))
	elif isinstance(transform, quat):		return 1/transform
	elif isinstance(transform, mat3):		return transpose(transform)
	elif isinstance(transform, mat4):
		rot = mat3(transform)
		inv = mat4(transpose(rot))
		inv[3] = vec4(- rot * transform[3])
		return inv
	else:
		raise typeError('transform must be a a tuple (translation, rotation), a quaternion, or a matrix')


def dichotomy_index(l, index, key=lambda x:x):
	start,end = 0, len(l)
	while start < end:
		mid = (start+end)//2
		val = key(l[mid])
		if val < index:		start =	mid+1
		elif val > index:	end =	mid
		else:	return mid
	return start
