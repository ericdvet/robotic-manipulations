"""move_joint controller."""

# You may need to import some classes of the controller module. Ex:
#  from controller import Robot, Motor, DistanceSensor
from time import time
from controller import Robot
from controller import Supervisor
from controller import Keyboard
import numpy as np
from math import *
from scipy.spatial.transform import Rotation as R
import random
#Define a table of fruit velocities to apply (x,y,z)
launchTable = [[0,0,8]]
maxFruit = 1
maxRobotReach = 1.3 - 0.1
ORIGIN = np.array([0,0,0.6])
gravity = 9.81
### WRITE FUNCTION TO SET FRUIT POSITION GIVEN ANGLE AND RADIUS FROM BASE OF THE ROBOT - SET TO GIVEN HEIGHT
def genFruitPos():
    fruitNode = supervisor.getFromDef('fruit0')
    translation_field = fruitNode.getField('translation')

    angle = random.uniform(0, 2 * pi)
    height = random.uniform(1, 3)
    radius = 4
    x = radius * cos(angle)
    y = radius * sin(angle)
    
    startingPosition = [x, y, height]
    translation_field.setSFVec3f(startingPosition)
    return startingPosition

### WRITE FUNCITON TO DETERMINE A RANDOM POINT ON SIDE THAT THE FRUIT IS PLACED
### WRITE FUNCITON TO DETERMINE NEEDED VELOCITIES TO GO FROM POINT OF FRUIT TO POINT OF ROBOT

def launchFruit():
    tof = random.uniform(1,2)
    fruitNode = supervisor.getFromDef('fruit0')
    targetX, targetY, targetZ = random.uniform(-maxRobotReach, maxRobotReach), random.uniform(-maxRobotReach, maxRobotReach), random.uniform(0.25, 1.25)
    translation_field = fruitNode.getField('translation')
    x, y, z = translation_field.getSFVec3f()
    velx = (targetX - x) / tof
    vely = (targetY - y) / tof
    velz = (targetZ - z + (1 / 2 * gravity * tof**2)) / tof
    fruitNode.setVelocity([velx, vely, velz, 0, 0, 0])
    fruitNode = None
    return ([velx, vely, velz], [targetX, targetY, targetZ])

def isTouched(caught):
    prevCaught = np.copy(caught)
    for fruitIndex in range(maxFruit):
        fruitNode = supervisor.getFromDef('fruit' + str(fruitIndex))
        trans_field = fruitNode.getField("translation")
        robotPos = [x_ee, y_ee, z_ee]
        diff = np.zeros(3)
        for i in range(3):
            diff[i] = trans_field.getSFVec3f()[i] - robotPos[i]
        if np.linalg.norm(diff) < 1.25:
            caught[fruitIndex] = 1
    if(not np.array_equal(prevCaught, caught)):
        print(caught)

def axis_euler(rot):
    x, y, z, angle = rot
    mag = sqrt(x*x + y*y + z*z)
    x /= mag
    z /= mag
    y /= mag
    yaw = atan2(y * sin(angle) - x*z*(1-cos(angle)), 1 - (y**2 + z**2 ) * (1 - cos(angle)))
    pitch = asin(x * y * (1 - cos(angle)) + z * sin(angle))
    roll = atan2(x * sin(angle)-y * z * (1 - cos(angle)) , 1 - (x**2 + z**2) * (1 - cos(angle)))
    return [-roll, -yaw, pitch]

def euler_axis(euler):
    c1 = cos(euler[0] / 2)
    c2 = cos(euler[1] / 2)
    c3 = cos(euler[2] / 2)
    s1 = sin(euler[0] / 2)
    s2 = sin(euler[1] / 2)
    s3 = sin(euler[2] / 2)
    
    x = s1 * s2 * c3 + c1 * c2 * s3
    y = s1 * c2 * c3 + c1 * s2 * s3
    z = c1 * s2 * c3 - s1 * c2 * s3
    
    angle = 2*acos(c1 * c2 * c3 - s1 * s2 * s3)
    
    return[x, y, z, angle]

def generate_H(theta, a, d, alpha):
    return np.asmatrix([[cos(theta), -sin(theta) * cos(alpha), sin(theta) * sin(alpha), a * cos(theta)], 
                        [sin(theta), cos(theta) * cos(alpha), -cos(theta) * sin(alpha), a * sin(theta)], 
                        [0, sin(alpha), cos(alpha), d], 
                        [0, 0, 0, 1]])

def generate_final_transform(theta_vals):
    alpha_vals = [pi/2, 0, 0, pi/2, -pi/2, 0]
    a_vals = [0, -0.6127, -0.57155, 0, 0, 0]
    d_vals = [0.1807, 0, 0, 0.17415, 0.11985, 0.11655]

    H_1 = generate_H(theta_vals[0], a_vals[0], d_vals[0], alpha_vals[0])
    H_2 = generate_H(theta_vals[1], a_vals[1], d_vals[1], alpha_vals[1])
    H_3 = generate_H(theta_vals[2], a_vals[2], d_vals[2], alpha_vals[2])
    H_4 = generate_H(theta_vals[3], a_vals[3], d_vals[3], alpha_vals[3])
    H_5 = generate_H(theta_vals[4], a_vals[4], d_vals[4], alpha_vals[4])
    H_6 = generate_H(theta_vals[5], a_vals[5], d_vals[5], alpha_vals[5])

    H_1_2 = H_1 @ H_2
    H_1_3 = H_1_2 @ H_3
    H_1_4 = H_1_3 @ H_4
    H_1_5 = H_1_4 @ H_5
    H_1_6 = H_1_5 @ H_6

    return H_1_6    

def create_jacobian(theta_vals):
    alpha_vals = [pi/2, 0, 0, pi/2, -pi/2, 0]
    a_vals = [0, -0.6127, -0.57155, 0, 0, 0]
    d_vals = [0.1807, 0, 0, 0.17415, 0.11985, 0.11655]

    H_1 = generate_H(theta_vals[0], a_vals[0], d_vals[0], alpha_vals[0])
    H_2 = generate_H(theta_vals[1], a_vals[1], d_vals[1], alpha_vals[1])
    H_3 = generate_H(theta_vals[2], a_vals[2], d_vals[2], alpha_vals[2])
    H_4 = generate_H(theta_vals[3], a_vals[3], d_vals[3], alpha_vals[3])
    H_5 = generate_H(theta_vals[4], a_vals[4], d_vals[4], alpha_vals[4])
    H_6 = generate_H(theta_vals[5], a_vals[5], d_vals[5], alpha_vals[5])

    H_1_2 = H_1 @ H_2
    H_1_3 = H_1_2 @ H_3
    H_1_4 = H_1_3 @ H_4
    H_1_5 = H_1_4 @ H_5
    H_1_6 = H_1_5 @ H_6

    r_0_0 = np.matrix([0,0,1]).astype('float')
    r_0_1 = np.transpose(H_1[0:3, 2])
    r_0_2 = np.transpose(H_1_2[0:3, 2])
    r_0_3 = np.transpose(H_1_3[0:3, 2])
    r_0_4 = np.transpose(H_1_4[0:3, 2])
    r_0_5 = np.transpose(H_1_5[0:3, 2])

    d_0_0 = np.transpose(np.matrix([[0], [0], [0]]))
    d_0_1 = np.transpose(H_1[0:3, 3])
    d_0_2 = np.transpose(H_1_2[0:3, 3])
    d_0_3 = np.transpose(H_1_3[0:3, 3])
    d_0_4 = np.transpose(H_1_4[0:3, 3])
    d_0_5 = np.transpose(H_1_5[0:3, 3])
    d_0_6 = np.transpose(H_1_6[0:3, 3])


    linear_jacobian = np.concatenate( (np.transpose(np.cross(r_0_0, d_0_6)), np.transpose(np.cross(r_0_1, (d_0_6-d_0_1))), \
        np.transpose(np.cross(r_0_2, (d_0_6-d_0_2))),np.transpose(np.cross(r_0_3, (d_0_6-d_0_3))), \
            np.transpose(np.cross(r_0_4, (d_0_6-d_0_4))), np.transpose(np.cross(r_0_5, (d_0_6-d_0_5)))), axis = 1)

    angular_jacobian = np.concatenate((np.transpose(r_0_0), np.transpose(r_0_1), np.transpose(r_0_2), np.transpose(r_0_3), \
        np.transpose(r_0_4), np.transpose(r_0_5)), axis = 1)

                                                                                                                                                         
    jacobian = np.concatenate((linear_jacobian, angular_jacobian), axis = 0)
    return jacobian

def calculate_error(given, goal):
    # Given is expected to be [x, y, z, yaw, pitch, roll]
    # Goal is given in [x_pos, y_pos, z_pos, x_axis, y_axis, z_axis, angle]
    euler_angles = axis_euler(goal[3:])
    return np.array([goal[0] - given[0],goal[1] - given[1],goal[2] - given[2] - 0.6, euler_angles[0] - given[3], euler_angles[1] - given[4], euler_angles[2] - given[5]])

def euler_from_Htrans(H):

    # beta = -np.arcsin(H[2,0])
    # alpha = np.arctan2(H[2,1]/np.cos(beta),H[2,2]/np.cos(beta))
    # gamma = np.arctan2(H[1,0]/np.cos(beta),H[0,0]/np.cos(beta))
    # return [alpha, beta, gamma]
    r = R.from_matrix(H[0:3, 0:3])
    r = r.as_euler('xyz', degrees = False)
    r = [r.item(0), r.item(1), r.item(2)]
    return r

def calculate_joint_vel(error, jacobian):
    kPt = 200
    kPa = 7.5
    # kPt = 3
    # kPa = 1
    scaled_error = np.concatenate((error[:3] * kPt, error[3:] * kPa), axis=0)
    # return np.linalg.inv(jacobian) @ scaled_error
    return scaled_error @ jacobian
    
def calculate_trajectory(x_init, y_init, z_init, x_vel, y_vel, z_vel, time_count):
    return [x_init+(x_vel*time_count) , y_init+(y_vel*time_count),  z_init+(z_vel*time_count) - ((gravity/2) * (time_count**2))]

supervisor = Supervisor()
# get the time step of the current world.
timestep = int(supervisor.getBasicTimeStep())
# timestep = 1

# Get the target position
target = supervisor.getFromDef('TARGET')
translation_field = target.getField('translation')
rotation_field = target.getField('rotation')




print('Using timestep: %d' % timestep)
# You should insert a getDevice-like function in order to get the
# instance of a device of the robot. Something like:
#  motor = robot.getDevice('motorname')
#  ds = robot.getDevice('dsname')
#  ds.enable(timestep)
# Initialize the arm motors and encoders.
motorNames = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint', 'wrist_1_joint', \
                'wrist_2_joint', 'wrist_3_joint']
motorDevices = []
for motorName in motorNames: 
    motor = supervisor.getDevice(motorName)
    motor.setPosition(0.0)
    motor.setVelocity(motor.getMaxVelocity()) #move at max speed
    position_sensor = motor.getPositionSensor()
    position_sensor.enable(timestep)
    motorDevices.append(motor)

#initialPos = [0, 0, 0, 0, 0, 0];
#initialPos = [-0.5, -0.5, -0.5, -0.5, -0.5, -0.5];
initialPos = [0, -1.57, 0.0, 0.0, 0.0, 0.0]
    
 # Initial position
for i in range(len(motorDevices)):
    motorDevices[i].setPosition(initialPos[i])

 
#Set up the first two joints for keyboard vel control
motionAxis = 0
#Enable vel control for the pan:
for i in range(len(motorDevices)):
    motorDevices[i].setPosition(float('+inf'))
    motorDevices[i].setVelocity(0.0)


#Start the pan operation going:
#motorDevices[motionAxis].setVelocity(1.0)

caught = np.zeros(4)

keyboard = Keyboard()
keyboard.enable(1) #sampling period (msec)

fruitDelay = 700 #time in between fruit launches
nextLaunch = fruitDelay #when is the next launch scheduled?
currentTime = 0
fruitIndex = 0
fruitLaunched = False

# Trajectory format is [x_{0}, y_{0}, z_{0}, x_vel, y_vel, z_vel]
x_init, y_init, z_init, x_vel, y_vel, z_vel = range(6)
fruit0_traj = [-0.5, 0.5, 0.05, launchTable[0][0], launchTable[0][1], launchTable[0][2]]

# Order is fruit 1 -> 2 -> 0 -> 3
base_time = supervisor.getTime()
print(base_time)
# pose0 = calculate_trajectory(fruit1_traj[x_init], fruit1_traj[y_init], fruit1_traj[z_init]-0.6, fruit1_traj[x_vel], fruit1_traj[y_vel], fruit1_traj[z_vel], 0.75)
# translation_field.setSFVec3f(pose0)
# rotation_field.setSFRotation([0, 1 ,0 ,pi/2])
while supervisor.step(timestep) != -1:
    # Read the sensors:
    # Enter here functions to read sensor data, like:
    #  val = ds.getValue()
    
    #if currentTime > nextLaunch and fruitIndex < maxFruit:
    #Time to launch some fruit!
    #print('Current time: %d Next Launch: %d' %(currentTime, nextLaunch))
    
    '''
    #It seems that webots has some trouble sequencing things - the velocities are set and can be verified
    #but the objects never move. But only when the velocity is applied after timestep 0...
    if currentTime > nextLaunch:
        if fruitIndex < maxFruit:
            print('Launching %d' % fruitIndex)
            launchFruit(fruitIndex)
            nextLaunch += fruitDelay
            fruitIndex += 1
    '''
    if not fruitLaunched:
        ballX, ballY, ballZ = genFruitPos()
        vels, targetPos = launchFruit()
        print('Launch all fruit!')
        # for i in range(0,maxFruit):
        #     launchFruit(i)
        fruitLaunched = True
        lastLaunch = currentTime

    if currentTime < 1.5:
        pose2 = calculate_trajectory(ballX, ballY, ballZ, vels[0], vels[1], vels[2], currentTime-0.01-lastLaunch)    
        translation_field.setSFVec3f(pose2)
    else:
        pose4 = [-0.18699999999999994, 0.645, 1.169352]
        translation_field.setSFVec3f(pose4)


                
            
    #getFruitVels()
    #endPos = endNode.getPosition()
    #endOrient = endNode.getOrientation()
    #print('Motion angle:' + str(motorDevices[motionAxis].getPositionSensor().getValue() % (2*math.pi)))
    #print(endPos)
    #print(endOrient)
 
   
    key = keyboard.getKey()
    if key == Keyboard.LEFT:
        motorDevices[0].setVelocity(motorDevices[0].getVelocity() + 0.1)
    elif key == Keyboard.RIGHT:
        motorDevices[0].setVelocity(motorDevices[0].getVelocity() - 0.1)     

    if key == Keyboard.UP:
        motorDevices[1].setVelocity(motorDevices[1].getVelocity() + 0.1)
    elif key == Keyboard.DOWN:
        motorDevices[1].setVelocity(motorDevices[1].getVelocity() - 0.1) 
    #print('Key: %d' % key)
    
    if key == ord('L'): #webots capitalizes all keys apparently
        if not fruitLaunched:
            print('Launch all fruit!')
            for i in range(0,maxFruit):
                launchFruit(i)
            fruitLaunched = True
            
    # currentTime += timestep/100
    currentTime = supervisor.getTime()

    motor_ang = []
    for motor in motorDevices:
        motor_ang.append(motor.getPositionSensor().getValue())

    jacobian = create_jacobian(motor_ang)
    H = generate_final_transform(motor_ang)
    x_ee,y_ee,z_ee = H[0,3], H[1, 3], H[2, 3]
    yaw, pitch, roll = euler_from_Htrans(H)
    current = [x_ee,y_ee,z_ee,yaw,pitch,roll]

    goal = translation_field.getSFVec3f()
    goal[0] *= -1
    goal[1] *= -1
    goal.extend(rotation_field.getSFRotation())
    
    error = calculate_error(current, goal)

    isTouched(caught)

    joint_vel = calculate_joint_vel(error, jacobian)
    i = 0
    for motor in motorDevices:
        # print(joint_vel.item(i))
        if abs(joint_vel.item(i)) > motor.getMaxVelocity():
            vel = (motor.getMaxVelocity() - 0.0001) * joint_vel.item(i) / abs(joint_vel.item(i))
            motor.setVelocity(vel)
        else:
            motor.setVelocity(joint_vel.item(i))


        i += 1

# Enter here exit cleanup code.
for i in range(len(motorDevices)):
    motorDevices[i].setVelocity(0.0)
