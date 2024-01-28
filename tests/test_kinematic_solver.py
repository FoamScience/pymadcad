from madcad.mathutils import *
from madcad.primitives import Axis
from madcad.kinematic import *
from madcad.joints import *
import numpy as np

print('1 free pivot')
print(Kinematic([
	Pivot((0,1), Axis(O,Y)),
	]).solve())

print('2 free pivots')
print(Kinematic([
	Pivot((0,1), Axis(O,Z)),
	Pivot((1,2), Axis(X,Z)),
	]).solve())

print('3 constrainted pivots')
print(Kinematic([
	Pivot((0,1), Axis(O,Z)),
	Pivot((1,2), Axis(X,Z)),
	Pivot((2,3), Axis(2*X,Z)),
	Weld((0,3), translate(-0.5*X)), 
	]).solve(close=np.random.random(3)))

print('3 pivots to inverse')
print(Kinematic(
	direct=[
		Pivot((0,1), Axis(O,Z)),
		Pivot((1,2), Axis(X,Z)),
		Pivot((2,3), Axis(2*X,Z)),
		],
	inverse=[Free((0,3))], 
	).inverse([translate(-0.5*X)], close=np.random.random(15)))

print('pivot loop')
print(Kinematic([
	Pivot((0,1), Axis(O,Z)),
	Pivot((1,2), Axis(X,Z)),
	Pivot((2,3), Axis(X+Y,Z)),
	Pivot((3,0), Axis(Y,Z)),
	]).solve(close=np.random.random(4)))

print('2 free pivot loops')
print(Kinematic([
	Pivot((0,1), Axis(O,Z)),
	Pivot((1,2), Axis(X,Z)),
	Pivot((2,3), Axis(X+Y,Z)),
	Pivot((3,0), Axis(Y,Z)),
	Pivot((2,4), Axis(X,Z)),
	Pivot((4,5), Axis(2*X,Z)),
	Pivot((5,6), Axis(2*X+Y,Z)),
	Pivot((6,2), Axis(X+Y,Z)),
	]).solve(close=np.random.random(8)))

print('2 bound pivot loops')
print(Kinematic([
	Pivot((0,1), Axis(O,Z)),
	Pivot((1,2), Axis(X,Z)),
	Pivot((2,3), Axis(X+Y,Z)),
	Pivot((3,0), Axis(Y,Z)),
	Pivot((1,4), Axis(2*X,Z)),
	Pivot((4,3), Axis(2*X+Y,Z)),
	]).solve(close=2*pi*np.random.random(6)))

print('stretched chain')
njoints = 80
joints = []
for i in range(0, njoints, 2):
	joints.append(Pivot((i,i+1), Axis(vec3(i+1,i,0), X)))
	joints.append(Pivot((i+1,i+2), Axis(vec3(i+1,i+1,0), Y)))
joints[-1].solids = (len(joints)-1, 0)
print(Kinematic(joints).solve(close=2*pi*np.random.random(len(joints))))

print('looping chain')
joints = []
for i in range(0, njoints, 2):
	joints.append(Pivot((i,i+1), Axis(X,X), Axis(O,X)))
	joints.append(Pivot((i+1,i+2), Axis(Y,Y), Axis(O,Y)))
joints[-1].solids = (len(joints)-1, 0)
print(Kinematic(joints).solve(close=2*pi*np.random.random(len(joints))))

print('grid')
size = 5
joints = []
def name(x,y):
	return '{}-{}'.format(x,y)
for x in range(size):
	for y in range(size):
		if x > 0:
			joints.append(Pivot((name(x-1,y), name(x,y)), Axis(vec3(1,0,0),Z), Axis(O,Z)))
		if y > 0:
			joints.append(Pivot((name(x,y-1), name(x,y)), Axis(vec3(0,1,0),Z), Axis(O,Z)))
print(Kinematic(joints).solve(close=2*pi*np.random.random(len(joints))))
