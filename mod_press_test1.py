"""
Team: RadSolutions
Author: David Foote, Ammon Black
***********************************************************************************************************************
Ammon's Notes:
This version adds two functions for use outside of the loops listed here.
calibrate and getTestData
***********************************************************************************************************************
Variable Definitions:
d = used to assign u3.U3() to a variable for easier use of the U3 module (Note: U3.py is written by LabJack)
pressureList_psi = List used to store measured pressure in pounds per sq inch (psi)
pressureList_Pa = List used to store measured pressure in Pascals (Pa)
temperatureList_degrees_F = List used to store measured temperature in degrees Fahrenheit (F)
temperatureList_Kelvin = List used to store measured temperature in Kelvin (K)
countTimeList = List used to store test sampling time in seconds (s)
minutes = number of minutes requested by the user to perform a leak check
testSamplingTime = Test sampling time requested by the user, stored in seconds (s)
pressure_psi_1 = Initial pressure (psi) reading taken at time = 0 s
pressure_Pa_1 = Initial pressure (Pa) reading taken at time = 0 s
ambientAirTemperature_F = Stores the ambient air temperature in degrees F
temperatureDifference = Stores the difference between the ambient air temperature and the temperature of the system
pressure_psi_2 = Pressure (psi) reading taken at time = 1 s
pressure_Pa_2 = Pressure (Pa) reading taken at time = 1 s
temperature_degrees_F_1 = Initial temperature (degrees F) reading taken at time = 0 s
temperature_Kelvin_1 = Initial temperature (Kelvin) reading taken at time = 0 s
temperature_degrees_F_2 = Temperature (degrees F) reading taken at time = 1 s
temperature_Kelvin_2 = Temperature (Kelvin) reading taken at time = 1 s
countTimePassed = variable used to count the total numbers of seconds that have passed
pressure_psi_n = Pressure (psi) reading taken at time = n
pressure_Pa_n = Pressure (Pa) reading taken at time = n
temperature_degrees_F_n = Temperature (degrees F) reading taken at time = n
temperature_Kelvin_n = Temperature (Kelvin) reading taken at time = n
leakTestResults = Boolean value (True or False). True indicates system is not leaking, False indicates a leak.
***********************************************************************************************************************
"""

import u3 # Calls LabJack U3 Module
from time import sleep # Used for thinking animation
import time
import xlsxwriter # Used to write data to Excel Workbook
import matplotlib.pyplot as plt # Used to plot graphs
import winsound
import statistics

# for use with getAmbientAirConditions() function
import sys
import subprocess
from idlelib.iomenu import encoding
import random # for testing only

d = u3.U3()
def calibrate():
    d.getCalibrationData()
    d.configIO(FIOAnalog=255)
    beepSound(frequency=500, duration=600, numberOfBeeps=3)

def text_run():
    # Display program start to the user
    print()
    print("*" * 100)
    print(" " * 29, "Initiating Rad.Solutions Leak Check Program")
    print("*" * 100)

    # prompt user to pressurize the system
    input("Pressurize annulus to 18-19 psi. Press Enter when complete: ")

    d = u3.U3()

    # d.getCalibrationData() reads in the U3's calibrations, so they can be applied to readings.
    # Section 2.6.2 of the LabJack User's Guide is helpful.
    # Sets up an internal calData dict for any future calls that need calibration.
    d.getCalibrationData()

    # Configure LabJack FIO pins to analog or digital:
    # By default the FIO pins are set to digital
    # The value you pass to set the pins as analog or digital is a bitmask value
    # 0 in any bit position indicates that port is set to digital and a 1 indicates analog.
    # Example:
    # Set FIO4 to analog 0001 1111b = 31
    # Set FIO5 to analog 0010 1111b = 47
    # Set FIO6 to analog 0100 1111b = 79
    # Set FIO7 to analog 1000 1111b = 143
    # Set FIO4 and FIO5 to analog 0011 1111b = 63
    # Set all FIO pins to analog 1111 1111b = 255
    # Set all FIO pins to digital 0000 1111b = 15
    d.configIO(FIOAnalog=255)  # All FIO pins set to analog

    minutes = float(input("\nEnter leak check minutes: "))
    testSamplingTime = minutes*60

    countTimePassed = 0

    print("\n" + "!" * 40, "\nBegin", minutes, "minute leak check.\n" + "!" * 40)
    beepSound(frequency=500, duration=600, numberOfBeeps=3)

    startTotalTime = time.time()

    loopControl = True
    global pressureList_psi, temperatureList_degrees_F, countTimeList, allowablePressureList_psi
    while loopControl == True:
        leakTestResults, pressureList_psi, temperatureList_degrees_F, countTimeList, lowPressure, allowablePressureList_psi \
            = leakTestControlLoop(d, countTimePassed, testSamplingTime)
        if leakTestResults == True and lowPressure == None:
            print("-"*40 + "\n" + "*"*40)
            print("Leak Check Passed.")
            loopControl = False
        elif leakTestResults == False and lowPressure == None:
            print("-"*40 + "\n" + "*"*40)
            print("Leak Check Failed due to an Actual Leak.")
            loopControl = False
        elif leakTestResults == None and lowPressure == None:
            print("-" * 40 + "\n" + "*" * 40)
            print("Leak Check Failed due to an Virtual Leak. \nThe leak check will automatically restart.")
            sleep(3)
            loopControl = True
        else:
            loopControl = False

    endTotalTime = time.time()
    totalTimePassed = endTotalTime - startTotalTime

    print("Total Test Time (hh:mm:ss): " + timeKeeper(totalTimePassed))
    print("*" * 40)


    if len(pressureList_psi) >= 2:
        # Plot results Pressure vs Time and Temperature vs Time
        plotResults(pressureList_psi, temperatureList_degrees_F, countTimeList, allowablePressureList_psi)

    programControl()

# For use without loop control will return units according to 'us' or 'metric' defaults metric
def  getTestData():
    temperature_degrees_F, temperature_K = getSystemTemperature(d)
    pressure_psi, pressure_Pa = getPressure(d)

    return {'temp_F':temperature_degrees_F, 'press_psi':pressure_psi, 'temp_K':temperature_K, 'press_Pa':pressure_Pa}



def leakTestControlLoop(d, countTimePassed, testSamplingTime):
    # Lists used to store data, write to Excel, and Plot Graphs
    pressureList_psi = []
    pressureList_Pa = []
    changeInPressureList_psi = []
    temperatureList_degrees_F = []
    temperatureList_Kelvin = []
    allowablePressureList_Pa = []
    allowablePressureList_psi = []
    countTimeList = []  # Stores time in seconds
    ambientAirTemperature_F_List = []
    pressure_atm_Pa_List = []

    temperature_degrees_F_1, temperature_Kelvin_1 = getSystemTemperature(d)
    pressure_psi_1, pressure_Pa_1 = getPressure(d)

    startTime = time.time()

    # While loop measures pressure and temperature every second and adds values to their respective list
    # It calls on the leak check function ratioTest() and counts time in seconds
    # It displays running pressure, temperature, time, and leak check results to the user
    # As long as a leak is not detected, the while loop will continue for the amount of time specified by testSamplingTime
    # If a leak is detected the While loop will stop
    global leakTestResults
    global lowPressure
    while countTimePassed < testSamplingTime:
        sleep(1)

        pressure_atm_Pa, ambientAirTemperature_F = getAmbientAirConditions()

        # Count seconds that pass and add to a list
        countTimeList.append(countTimePassed)

        # Measure pressure and temperature every second
        # Display measured pressure and temperature to the user
        print("-" * 40)
        pressure_psi_n, pressure_Pa_n = getPressure(d)
        temperature_degrees_F_n, temperature_Kelvin_n = getSystemTemperature(d)


        # Add measured pressure and temperature values to a list
        pressureList_psi.append(pressure_psi_n)
        pressureList_Pa.append(pressure_Pa_n)
        temperatureList_degrees_F.append(temperature_degrees_F_n)
        temperatureList_Kelvin.append(temperature_Kelvin_n)
        pressure_atm_Pa_List.append(pressure_atm_Pa)
        ambientAirTemperature_F_List.append(ambientAirTemperature_F)


        print("Pressure =", str(format(pressure_psi_n, ".2f")), "psi")
        print("Temperature =", str(format(temperature_degrees_F_n, ".1f")), "\N{DEGREE SIGN}F")


        # Send initial reference pressure and temperature values as well as current pressure and temperature values
        # to allowablePressureTest() function to perform leak
        leakTestResults, allowablePressure_Pa, allowablePressure_psi, change_in_pressure_psi = \
            allowablePressureTest(pressure_Pa_1, pressure_psi_1, pressure_psi_n, temperature_Kelvin_1,
                                  temperature_Kelvin_n, pressure_atm_Pa)

        allowablePressureList_Pa.append(allowablePressure_Pa)
        allowablePressureList_psi.append(allowablePressure_psi)
        changeInPressureList_psi.append(change_in_pressure_psi)

        endTime = time.time()
        countTimePassed = endTime - startTime
        print("Time (hh:mm:ss): " + timeKeeper(countTimePassed))
        print("-" * 40)

        # If else loop displays results of the leak check to the user
        # If no leak is detected the While Loop will continue
        # If a leak is detected the while loop will stop and results will be displayed to the user
        if leakTestResults == True and pressure_psi_n > allowablePressure_psi:
            print("A leak has NOT been detected.")

            lowPressure = lowPressureWarning(pressure_psi_n, allowablePressure_psi, pressureList_psi)
            if lowPressure == True:
                sleep(1)
                break

        elif leakTestResults == True and pressure_psi_n <= allowablePressure_psi:
            print("A Possible Leak has been detected. "
                  "\nHowever, the pressure loss has not exceeded 0.1 psi. "
                  "\nThe leak is within limits.")

            lowPressure = lowPressureWarning(pressure_psi_n, allowablePressure_psi, pressureList_psi)
            if lowPressure == True:
                sleep(1)
                break

        elif leakTestResults == False:
            print("!"*10 + " WARNING " + "!"*10 + "\nThe pressure has decreased more that 0.1 psi. "
                  "\nA Possible leak has been detected. Troubleshoot as required.")

            lowPressure = lowPressureWarning(pressure_psi_n, allowablePressure_psi, pressureList_psi)
            if lowPressure == True:
                sleep(1)
                break

            else:
                beepSound(frequency=500, duration=600, numberOfBeeps=10)
                sleep(1)
                break

        else:
            print("Note: \nThe pressure has decreased more that 0.1 psi. "
                  "\nThe pressure decrease was likely due to decreasing temperatures. "
                  "\nContinue running the leak check until thermal equilibrium is achieved.")
            beepSound(frequency=500, duration=600, numberOfBeeps=5)
            sleep(1)
            break

    # Sound end of leak check
    beepSound(frequency=500, duration=2000, numberOfBeeps=1)

    if len(pressureList_psi)>=2:

        # Statistical data of actual pressure and allowable pressure
        meanPressure_psi = statistics.mean(pressureList_psi)
        stdDev_Pressure_psi = statistics.stdev(pressureList_psi)

        meanPressure_Pa = statistics.mean(pressureList_Pa)
        stdDev_Pressure_Pa = statistics.stdev(pressureList_Pa)

        meanAllowablePressure_psi = statistics.mean(allowablePressureList_psi)
        stdDev_AllowablePressure_psi = statistics.stdev(allowablePressureList_psi)

        meanAllowablePressure_Pa = statistics.mean(allowablePressureList_Pa)
        stdDev_AllowablePressure_Pa = statistics.stdev(allowablePressureList_Pa)

        meanTemperature_Kelvin = statistics.mean(temperatureList_Kelvin)
        stdDev_Temperature_Kelvin = statistics.stdev(temperatureList_Kelvin)

        meanTemperature_degrees_F = statistics.mean(temperatureList_degrees_F)
        stdDev_Temperature_degrees_F = statistics.stdev(temperatureList_degrees_F)

        meanChangeInPressure_psi = statistics.mean(changeInPressureList_psi)
        stdDev_ChangeInPressure_psi = statistics.stdev(changeInPressureList_psi)

        # Write the measured pressure and temperature data stored in lists to an Excel Workbook
        writeToExcel(pressureList_psi, pressureList_Pa, temperatureList_degrees_F, temperatureList_Kelvin,
                     allowablePressureList_psi, allowablePressureList_Pa, countTimeList, ambientAirTemperature_F_List,
                     pressure_atm_Pa_List, meanPressure_psi, stdDev_Pressure_psi,  meanPressure_Pa, stdDev_Pressure_Pa,
                     meanAllowablePressure_psi, stdDev_AllowablePressure_psi, meanAllowablePressure_Pa,
                     stdDev_AllowablePressure_Pa, meanTemperature_Kelvin, stdDev_Temperature_Kelvin,
                     meanTemperature_degrees_F, stdDev_Temperature_degrees_F, changeInPressureList_psi,
                     meanChangeInPressure_psi, stdDev_ChangeInPressure_psi)

    return leakTestResults, pressureList_psi, temperatureList_degrees_F, countTimeList, lowPressure, \
           allowablePressureList_psi

def getPressure(d):
    '''When called this function returns measured pressure in psi and Pa.

    # FIOpinNumber = FIO pin number on LabJack U3-HV that the pressure transducer is plugged into.
    # This value will change based on which FIO pin the pressure transducer is connect to:
    # Note: On U3-HV do not use the AIO pins.'''
    # The AIO pins are used for high voltage inputs and do not accurately measure small voltage changes.
    # 0 - 3   = AIN0 - AIN3
    # 4 - 7   = FIO4 - FIO7
    # 8 - 15  = EIO0 - EIO7
    # 16 - 19 = CIO0 - CIO3
    FIOpinNumber = 6

    pressureVoltageList = []

    global averagePressureVoltage

    # This for loop calculates the average voltage produced by the pressure sensor
    for i in range(50):

        measuredVolts = (d.getAIN(FIOpinNumber))
        pressureVoltageList.append(measuredVolts)
        averagePressureVoltage = statistics.mean(pressureVoltageList)

    pressure_psi = 15.82504477 * averagePressureVoltage - 7.26430736 # In psi
    pressure_Pa = pressure_psi * 6894.757 # returns pressure in Pascals

    return pressure_psi, pressure_Pa

def getAmbientAirConditions():
    '''
    This function will be used to access the atmospheric sensor. For now it only returns barometric pressure and
    temperature in degrees F. Can also return relative humidity if needed.
    '''
    try:
        p = subprocess.check_output(["usbtenkiget", "-i", "1, 2, 0"])
    except subprocess.CalledProcessError:
        print("usbtenkiget error")
        sys.exit(1)

    p = str(p, encoding)
    fields = p.split(", ")

    # Detect errors by checking if the exact expected number fields was returned.
    if len(fields) < 3:
        print("Error reading sensor")
        sys.exit(2)

    # Convert the fields from strings to floating point values
    # This step is necessary, otherwise math on values will not
    # be possible.
    temperature = float(fields[0]) # Temperature in degrees C
    rh = float(fields[1]) # Relative Humidity
    pressure = float(fields[2])*1000 # In Pascals
    tempF = temperature * 9 / 5 + 32 # Temperature in degrees F

    '''# Display values
    print("Temperature (C):", temperature)
    print("RH......... (%):", rh)
    print("Pressure..(kPa):", pressure)
    print("Temperature (F):", tempF)

    sys.exit(0)
    pressure = random.randint(101300, 101600)
    tempF = random.randint(60,70)'''
    return pressure, tempF

def getSystemTemperature(d):
    "When called this function returns temperature value in degrees F and Kelvin"

    # FIOpinNumber = FIO pin number on LabJack U3-HV that the pressure transducer is plugged into.
    # This value will change based on which FIO pin the pressure transducer is connect to:
    # Note: On U3-HV do not use the AIO pins.
    # The AIO pins are used for high voltage inputs and do not accurately measure small voltage changes.
    # 0 - 3   = AIN0 - AIN3
    # 4 - 7   = FIO4 - FIO7
    # 8 - 15  = EIO0 - EIO7
    # 16 - 19 = CIO0 - CIO3
    FIOpinNumber = 4

    temperatureVoltageList = []

    global averageTemperatureVoltage

    # This for loop calculates the average voltage produced by the temperature sensor
    for i in range(50):
        measuredVoltsTemperature = (d.getAIN(FIOpinNumber))
        temperatureVoltageList.append(measuredVoltsTemperature)
        averageTemperatureVoltage = statistics.mean(temperatureVoltageList)

    temperature_degrees_F = 100 * averageTemperatureVoltage

    temperature_degrees_C = (5/9)*(temperature_degrees_F-32)

    temperature_Kelvin = temperature_degrees_C + 273.15

    return temperature_degrees_F, temperature_Kelvin

def allowablePressureTest(pressure_Pa_1, pressure_psi_1, pressure_psi_n, temperature_Kelvin_1,
                                  temperature_Kelvin_n, pressure_atm_Pa):
    '''This function uses the ideal gas law to calculate the pressure expected due to changing temperatures
    (allowable pressure).Then a tolerance value is subtracted from the allowable pressure to shift the allowable
    pressure values away from the actual values by the amount defined by the tolerance.'''

    #tolerance = 344.7379   # 0.05 psi, gives false leak indications during rapidly decreasing temps
    tolerance = 413.6854   # 0.06 psi, This works the best for rapidly decreasing temps
    #tolerance = 482.633    # 0.07 psi
    #tolerance = 551.5806   # 0.08 psi
    #tolerance = 620.5281   # 0.09 psi
    #tolerance = 689.4757   # 0.1 psi


    allowablePressure_Pa = (temperature_Kelvin_n / temperature_Kelvin_1) * (
                pressure_Pa_1 + pressure_atm_Pa) - pressure_atm_Pa - tolerance

    allowablePressure_psi = allowablePressure_Pa / 6894.757

    print("allowable Pressure =", round(allowablePressure_psi, 2), "psi")

    change_in_pressure_psi = round(pressure_psi_n - pressure_psi_1,2)
    print("Change in pressure =", change_in_pressure_psi, "psi")

    if change_in_pressure_psi <= -0.1:
        if pressure_psi_n >= allowablePressure_psi:
            # When pressure loss is due to decrease in temperature
            return None, allowablePressure_Pa, allowablePressure_psi, change_in_pressure_psi
        else:
            # When pressure loss is due to possible leak
            return False, allowablePressure_Pa, allowablePressure_psi, change_in_pressure_psi
    else:
        return True, allowablePressure_Pa, allowablePressure_psi, change_in_pressure_psi

def timeKeeper(countTimePassed):
    '''When called displays time to the user in the following format: hh:mm:ss'''

    timeSec = int(countTimePassed)
    timeMin = int(timeSec / 60)
    timeHr = int(timeMin / 60)

    # Calculates seconds 0-59 after minute counter is greater than zero ex: 00:01:30
    timeSec_f = int(timeSec - timeMin * 60)

    # Calculates minutes 0-59 after hour counter is greater than zero ex: 01:30:30
    timeMin_f = int(timeMin - timeHr * 60)

    return str(timeHr).rjust(2, '0') + ":" + str(timeMin_f).rjust(2, '0') + ":" + \
           str(timeSec_f).rjust(2, '0')

def writeToExcel(saveDestination, pressureList_psi, pressureList_Pa, temperatureList_degrees_F, temperatureList_Kelvin,
                 allowablePressureList_psi, allowablePressureList_Pa, countTimeList, ambientAirTemperature_F_List,
                 pressure_atm_Pa_List, meanPressure_psi, stdDev_Pressure_psi,  meanPressure_Pa, stdDev_Pressure_Pa,
                 meanAllowablePressure_psi, stdDev_AllowablePressure_psi, meanAllowablePressure_Pa,
                 stdDev_AllowablePressure_Pa, meanTemperature_Kelvin, stdDev_Temperature_Kelvin,
                 meanTemperature_degrees_F, stdDev_Temperature_degrees_F, changeInPressureList_psi,
                 meanChangeInPressure_psi, stdDev_ChangeInPressure_psi):
    # When called writes data contained in lists to an Excel Workbook

    # Create file workbook and worksheet to add temperature data to
    Leak_Test_Results_Workbook = xlsxwriter.Workbook(saveDestination+".xlsx")
    Leak_Test_Results_Sheet = Leak_Test_Results_Workbook.add_worksheet()

    # Send titles to Excel file
    Leak_Test_Results_Sheet.set_column("A:M", 30)
    Leak_Test_Results_Sheet.write("A1", "Ambient Air Temperature (F)")
    Leak_Test_Results_Sheet.write("B1", "Atmospheric Pressure (Pa)")
    Leak_Test_Results_Sheet.write("C1", "Pressure (psi)")
    Leak_Test_Results_Sheet.write("D1", "Pressure (Pa)")
    Leak_Test_Results_Sheet.write("E1", "Temperature (F)")
    Leak_Test_Results_Sheet.write("F1", "Temperature (K)")
    Leak_Test_Results_Sheet.write("G1", "Allowable Pressure (psi)")
    Leak_Test_Results_Sheet.write("H1", "Allowable Pressure (Pa)")
    Leak_Test_Results_Sheet.write("I1", "Time (s)")
    Leak_Test_Results_Sheet.write("J1", "Change in pressure (psi)")

    # Send temperature, pressure, and time data to Excel file
    for i in range(len(pressureList_psi)):
        Leak_Test_Results_Sheet.write(i + 1, 0, ambientAirTemperature_F_List[i])
        Leak_Test_Results_Sheet.write(i + 1, 1, pressure_atm_Pa_List[i])
        Leak_Test_Results_Sheet.write(i + 1, 2, pressureList_psi[i])
        Leak_Test_Results_Sheet.write(i + 1, 3, pressureList_Pa[i])
        Leak_Test_Results_Sheet.write(i + 1, 4, temperatureList_degrees_F[i])
        Leak_Test_Results_Sheet.write(i + 1, 5, temperatureList_Kelvin[i])
        Leak_Test_Results_Sheet.write(i + 1, 6, allowablePressureList_psi[i])
        Leak_Test_Results_Sheet.write(i + 1, 7, allowablePressureList_Pa[i])
        Leak_Test_Results_Sheet.write(i + 1, 8, countTimeList[i])
        Leak_Test_Results_Sheet.write(i + 1, 9, changeInPressureList_psi[i])

    # Send statistical Data to Excel File
    Leak_Test_Results_Sheet.write("L1", "Mean Pressure (psi)")
    Leak_Test_Results_Sheet.write(0, 12, meanPressure_psi)

    Leak_Test_Results_Sheet.write("L2", "Std Dev Pressure (psi)")
    Leak_Test_Results_Sheet.write(1, 12, stdDev_Pressure_psi)

    Leak_Test_Results_Sheet.write("L3", "Mean Pressure (Pa)")
    Leak_Test_Results_Sheet.write(2, 12, meanPressure_Pa)

    Leak_Test_Results_Sheet.write("L4", "Std Dev Pressure (Pa)")
    Leak_Test_Results_Sheet.write(3, 12, stdDev_Pressure_Pa)

    Leak_Test_Results_Sheet.write("L5", "Mean Allowable Pressure (psi)")
    Leak_Test_Results_Sheet.write(4, 12, meanAllowablePressure_psi)

    Leak_Test_Results_Sheet.write("L6", "Std Dev Allowable Pressure (psi)")
    Leak_Test_Results_Sheet.write(5, 12, stdDev_AllowablePressure_psi)

    Leak_Test_Results_Sheet.write("L7", "Mean Allowable Pressure (Pa)")
    Leak_Test_Results_Sheet.write(6, 12, meanAllowablePressure_Pa)

    Leak_Test_Results_Sheet.write("L8", "Std Dev Allowable Pressure (Pa)")
    Leak_Test_Results_Sheet.write(7, 12, stdDev_AllowablePressure_Pa)

    Leak_Test_Results_Sheet.write("L9", "Mean Temperature (K)")
    Leak_Test_Results_Sheet.write(8, 12, meanTemperature_Kelvin)

    Leak_Test_Results_Sheet.write("L10", "Std Dev Temperature (K)")
    Leak_Test_Results_Sheet.write(9, 12, stdDev_Temperature_Kelvin)

    Leak_Test_Results_Sheet.write("L11", "Mean Temperature (F)")
    Leak_Test_Results_Sheet.write(10, 12, meanTemperature_degrees_F)

    Leak_Test_Results_Sheet.write("L12", "Std Dev Temperature (F)")
    Leak_Test_Results_Sheet.write(11, 12, stdDev_Temperature_degrees_F)

    Leak_Test_Results_Sheet.write("L13", "Mean Change in pressure (psi)")
    Leak_Test_Results_Sheet.write(12, 12, meanChangeInPressure_psi)

    Leak_Test_Results_Sheet.write("L14", "Std Dev Change in pressure (psi)")
    Leak_Test_Results_Sheet.write(13, 12, stdDev_ChangeInPressure_psi)

    # Close workbook to save results
    # Note: if previous Leak_Test_Results.xlsx file is opened when close() is called the program will crash
    # Ensure all previous versions of Leak_Test_Results.xlsx are closed before running program
    Leak_Test_Results_Workbook.close()

def plotResults(pressureList_psi,temperatureList_degrees_F,countTimeList, allowablePressureList_psi):
    '''when called displays plot of Pressure (psi) vs Time (s) and Temperature (degrees F) vs Time (s) to the user'''

    # Plot Pressure vs Time
    plt.plot(countTimeList, pressureList_psi, 'b')
    plt.title('Pressure Vs. Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Pressure (psi)')
    plt.show()

    # Plot temperature vs Time
    plt.plot(countTimeList, temperatureList_degrees_F, 'r')
    plt.title('Temperature Vs. Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Temperature (\N{DEGREE SIGN}F)')
    plt.show()

def beepSound(frequency, duration, numberOfBeeps):
    '''When called produces a number of beeps for the frequency and duration specified'''

    for i in range(0, numberOfBeeps):
        winsound.Beep(frequency, duration)

def lowPressureWarning(pressure_psi_n, allowablePressure_psi, pressureList_psi):
    if pressure_psi_n < 18 and pressure_psi_n > allowablePressure_psi and len(pressureList_psi) >= 2:
        print()
        print("!" * 10 + "WARNING LOW PRESSURE DETECTED" + "!" * 10 +
              "\nDue to changing temperatures, the pressure decreased below 18 psi."
              "\nRe-pressurize the system and run the leak check again.")
        beepSound(frequency=500, duration=600, numberOfBeeps=5)
        return True

    elif pressure_psi_n < 18 and pressure_psi_n <= allowablePressure_psi and len(pressureList_psi) >= 2:
        print()
        print("!" * 10 + "WARNING LOW PRESSURE DETECTED" + "!" * 10 +
              "\nDue to a possible leak, the pressure decreased below 18 psi. "
              "\nTroubleshoot as required and run the leak check again.")
        beepSound(frequency=500, duration=600, numberOfBeeps=5)
        return True

    elif pressure_psi_n < 18 and len(pressureList_psi) < 2:
        print()
        print("!" * 10 + "WARNING LOW PRESSURE DETECTED" + "!" * 10 +
              "\nThe pressure is below 18 psi."
              "\nRe-pressurize the system and run the leak check again.")
        beepSound(frequency=500, duration=600, numberOfBeeps=5)
        return True

def programControl():
    # Ask user to restart or close the program

    programControl = True
    while programControl == True:
        print("\nDo you want to restart the leak check?")
        close = str.capitalize(input("Input Y and press Enter to restart, or input N and press Enter to quit: "))
        if close == "Y":
            programControl = False
            main()
        elif close == "N":
            programControl = False
        else:
            print("\nYour response was not recognized.")
            programControl = True
