from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
import matplotlib, time, sys, pickle
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import PySimpleGUI as sg
import numpy as np
import mod_press_test1 as mpt

class Pressure_Test_UI:
    def __init__(self):
        self._small_text_size = 12
        self._large_text_size = 20
        self._font = 'Times '
        self._default_element_size = (30,1)
        self._units = 'us'

        self._display_timer = True
        self._display_PTime_plt = True
        self._display_PTemp_plt = False
        self._display_leak_rate = True
        self._display_TempTime_plt =  False
        self._plot_update_rate = 10
        self._plot_allowable_press = False
        self._test_data = {'time':[], 'press_psi':[], 'press_Pa':[], 'temp_F':[], 'temp_K':[], 'len':0,
                'alPress_psi':[], 'alPress_Pa':[], 'amb_T_F':[],'amb_P_Pa':[], 'press_change_psi':[]}
        self._plot_data = {'time':[],  'pressure':[], 'all_pressure':[]} # The variables filled here by self.__plt_maker
        self._test_duration = 15*60*100 # We need to capture milliseconds
        self._leak_tolerance_psi = 0.1  # The leak tolerance set by INL
        self._pressure_low_bound = 18  # The lower bound of acceptable pressure
        self._delta_time = 2
        try:
            tmp = self.load('saved_settings.pck')

            self._small_text_size = tmp._small_text_size
            self._large_text_size = tmp._large_text_size
            self._font = tmp._font
            self._default_element_size = tmp._default_element_size
            self._units = tmp._units

            self._display_timer = tmp._display_timer
            self._display_PTime_plt = tmp._display_PTime_plt
            self._display_PTemp_plt = tmp._display_PTemp_plt
            self._display_leak_rate = tmp._display_leak_rate
            self._display_TempTime_plt = tmp._display_TempTime_plt
            self._plot_update_rate = tmp._plot_update_rate
            self._test_duration = tmp._test_duration
        except FileNotFoundError:
            print("No saved file found")

        self.timer_layout = None
        self.pTime_layout = None
        self.pTemp_layout = None
        self.leak_rate_layout = None
        self.TempTime_layout = None
        self.test_window = None

        sg.SetOptions(element_padding=(15,1))

    # save() function to save the trained network to a file
    def save(self, obj, file_name):
        with open(file_name, 'wb') as fp:
            pickle.dump(obj, fp)

    # restore() function to restore the file
    def load(self, file_name):
        with open(file_name, 'rb') as fp:
            obj = pickle.load(fp)
        return obj

    # These functions will produce an updating matplotlib window

    class PBR:
        def __init__(self, value):
            self.v = value

    def __plt_maker(self, window): # this should be called as a thread, then time.sleep() here would not freeze the GUI
        # The _plot_update_rate should never be smaller than the _delta_time
        number_to_reduce = self._plot_update_rate // self._delta_time

        # We slice off the  number of points to reduce and attach them to the end of the _plot_data
        #   We also change the time from milliseconds to seconds
        self._plot_data['time'].append(np.median(self._test_data['time'][ self._test_data['len']-number_to_reduce :: ])//100)
        self._plot_data['pressure'].append(np.mean(self._test_data['press_psi'][ self._test_data['len']-number_to_reduce :: ]))
        if self._plot_allowable_press:
            self._plot_data['all_pressure'].append(np.mean(self._test_data['press_change_psi'][ self._test_data['len']-number_to_reduce :: ]))
            plt.plot(self._plot_data['time'], self._plot_data['pressure'], 'b')
            plt.plot(self._plot_data['time'], self._plot_data['pressure'], 'r')
        else:
            plt.plot(self._plot_data['time'], self._plot_data['pressure'], 'b')
        window.write_event_value('-THREAD-', 'done.')
        return plt.gcf()

    def __draw_figure(self, canvas, figure, loc=(0, 0)):
        figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        return figure_canvas_agg


    def __delete_fig_agg(self, fig_agg):
        fig_agg.v.get_tk_widget().forget()
        plt.close('all')

    def make_plot_layout(self, plot_type='Pressure vs Time'):
        # define the window layout
        plot_layout = [ # [sg.Button('update'), sg.Button('Stop', key="-STOP-"), sg.Button('Exit', key="-EXIT-")],
                  [sg.Radio('Update Plot', "RADIO1", default=True, size=(12,3),key="-LOOP-"),sg.Radio('Stop Plot Update', "RADIO1", size=(12,3), key='-NOLOOP-')],
                  [sg.Text(plot_type, font=self._font+str(self._large_text_size))],
                  [sg.Canvas(size=(500,500), key='canvas')]]

        # create the form and show it without the plot
        # plot_window = sg.Window('Demo Application - Embedding Matplotlib In PySimpleGUI',
        #                   plot_layout, finalize=True)

        return plot_layout

    def make_timer_layout(self):
        timer_layout = [   [sg.Text('Time', size=(8,1), font=self._font+ str(self._small_text_size), justification='center')],
                        [sg.Text('', size=(8,2), font=self._font+str(self._large_text_size), background_color='black', justification='center', key='time')],
                        #[sg.Button('Reset')]
                        ]

        # timer_window = sg.Window('Running Timer', timer_layout)
        return timer_layout

    def make_text_element(self):
        text_element = [[sg.Text('Status', size=(8,1), font=self._font+ str(self._small_text_size), justification='center') ],
                        [sg.Text('Test is Running', size=(8,2), font=self._font+ str(self._large_text_size+4), justification='center', key='text output')]
                        ]
        return text_element

    def make_press_element(self):
        press_element = [[sg.Text('Pressure', size=(8,1), font=self._font+ str(self._small_text_size), justification='center') ],
                        [sg.Text('', size=(8,2), font=self._font+str(self._large_text_size), background_color='black', justification='center', key='press')],
                        ]
        return press_element

    def _plot_checker(self, window, event, values, fig_agg):
        #import pdb; pdb.set_trace()
        if values['-NOLOOP-'] == False:
            window.write_event_value('-THREAD-', 'done.')
            event=="-THREAD-"

        if event == "update":
            if fig_agg.v is not None:
                    self.__delete_fig_agg(fig_agg)
            fig = self.__plt_maker(window)
            fig_agg.v = self.draw_figure(window['canvas'].TKCanvas, fig)


        if event == "-THREAD-":
            if values['-LOOP-'] == True:
                if fig_agg.v is not None:
                    self.__delete_fig_agg(fig_agg)
                fig = self.__plt_maker(window)
                fig_agg.v = self.__draw_figure(window['canvas'].TKCanvas, fig)
                window.Refresh()



    def _timer_checker(self, window, event, values, current_time):
        # --------- Display timer in window --------
        window['time'].update('{:02d}:{:02d}.{:02d}'.format((current_time // 100) // 60, (current_time // 100) % 60, current_time % 100), font=self._font+ str(self._large_text_size), background_color='black')

    def _pres_updater(self, window, event, values, press):
        window['press'].update(str(press)+ " psi")

    def _text_updater(self, window, text, text_color='white', background_color='green'):
        # --------- Display timer in window --------
        window['text output'].update(text, background_color=background_color, text_color=text_color)

    def run_test_window(self):
        # Calibrate labjack
        mpt.calibrate()

        # This is a helper function meant to simplify the code below it contains most of the work loop logic
        def handle_data(self, test_window):
            data = mpt.getTestData()

            # We want to update all of our lists in our data with the appropriate information
            self._test_data['time'].append(current_time)
            self._test_data['press_Pa'].append(data['press_Pa'])
            self._test_data['temp_K'].append(data['temp_K'])
            self._test_data['press_psi'].append(data['press_psi'])
            self._test_data['temp_F'].append(data['temp_F'])
            self._test_data['len']+=1

            pressure_atm_Pa, ambientAirTemperature_F = mpt.getAmbientAirConditions()
            self._test_data['amb_P_Pa'].append(pressure_atm_Pa)
            self._test_data['amb_T_F'].append(ambientAirTemperature_F)

            # The following will run similar to leakTestControlLoop # This could be cleaned up <<<<<<<<<<<<<<<<<<<<<<<<<
            leakTestResults, allowablePressure_Pa, allowablePressure_psi, change_in_pressure_psi = \
                mpt.allowablePressureTest(self._test_data['press_Pa'][0], self._test_data['press_psi'][0],
                    self._test_data['press_psi'][self._test_data['len']-1], self._test_data['temp_K'][0],
                    self._test_data['temp_K'][self._test_data['len']-1], pressure_atm_Pa)

            self._test_data['alPress_Pa'].append(allowablePressure_Pa)
            self._test_data['alPress_psi'].append(allowablePressure_psi)
            self._test_data['press_change_psi'].append(change_in_pressure_psi)

            pressure_psi_n = self._test_data['press_psi'][self._test_data['len']-1]

            # THESE IF ELSE STATEMENTS ARE CONFUSSING AF<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            if leakTestResults == True and pressure_psi_n > allowablePressure_psi:
                self._text_updater(test_window, "No leak detected")

                lowPressure = mpt.lowPressureWarning(pressure_psi_n, allowablePressure_psi, self._test_data['press_psi'])
                if lowPressure == True:
                    return  False, False, False, True
                return True, False, False, False

            elif leakTestResults == True and pressure_psi_n <= allowablePressure_psi:
                self._text_updater(test_window, "Possible leak detected", 'black', 'yellow')
                """
                print("A Possible Leak has been detected. "
                      "\nHowever, the pressure loss has not exceeded 0.1 psi. "
                      "\nThe leak is within limits.")
                """
                lowPressure = mpt.lowPressureWarning(pressure_psi_n, allowablePressure_psi, self._test_data['press_psi'])
                if lowPressure == True:
                    return False, False, False, True
                return True, False, True, False

            elif leakTestResults == False:
                self._text_updater(test_window, "FAIL\nDecreased "+str(self._leak_tolerance_psi)+" psi", 'white', 'red')

                lowPressure = mpt.lowPressureWarning(pressure_psi_n, allowablePressure_psi, self._test_data['press_psi'])
                if lowPressure == True:
                    return False, False, False, True

                else:
                    mpt.beepSound(frequency=500, duration=400, numberOfBeeps=1)
                    return False, True, False, False


            else:
                self._text_updater(test_window, "FAIL\nVirtual", 'black', 'yellow')
                """
                print("Note: \nThe pressure has decreased more that 0.1 psi. "
                      "\nThe pressure decrease was likely due to decreasing temperatures. "
                      "\nContinue running the leak check until thermal equilibrium is achieved.")
                """
                mpt.beepSound(frequency=500, duration=400, numberOfBeeps=1)
                return False, True, True, False

        # Check the true and Falses (NOT IMPLEMENTED) # This could be implemented <<<<<<<<<<<<<<<<<<<<<<<<<
        test_layout = self.make_timer_layout()
        test_layout[0].extend(self.make_text_element()[0])
        test_layout[1].extend(self.make_text_element()[1])
        test_layout[0].extend(self.make_press_element()[0])
        test_layout[1].extend(self.make_press_element()[1])
        test_layout.extend(self.make_plot_layout())

        test_window = sg.Window("Test Window", test_layout, finalize=True)

        start_time = int(round(time.time() * 100))

        fig_agg = self.PBR(None) # My work around class for pass by refrence
        # Used in the logic for deciding when to  update plot and collect data
        update_plot = True
        collect_data  = True
        data = {}

        # The following variables are used after the test finishes
        run_test, leak_detected, temp_related, low_pressure = True, False, False, False


        while True:
            # Handle window exiting
            event, values = test_window.read(timeout=10)
            if event is None:  # if user closes window
                break
            if event == "-EXIT-":
                break
            """
            if event == 'Reset':
                self._plot_data = {'time':[],  'pressure':[], 'all_pressure':[]}
                start_time = int(round(time.time() * 100))
            """
            current_time = int(round(time.time() * 100)) - start_time


            # Start logic to collect data and run window This is where all of the other functions are called
            if current_time < self._test_duration and run_test:

                # Fill the test data stored in _test_data. If we want to make it better
                #   we can add average of many samples

                # Only collect data according to self._delta_time interval
                if self._delta_time != 1:
                    if (current_time // 100) % self._delta_time == 0 and collect_data:
                        run_test, leak_detected, temp_related, low_pressure = handle_data(self, test_window)
                        collect_data = False
                        self._pres_updater(test_window, event, values, round(self._test_data['press_psi'][self._test_data['len']-1], 3))

                    if not collect_data and (current_time // 100) % self._delta_time != 0:
                        collect_data = True
                else:
                    if (current_time % 100) < 50 and collect_data:
                        run_test, leak_detected, temp_related, low_pressure = handle_data(self, test_window)
                        collect_data = False
                        self._pres_updater(test_window, event, values, round(self._test_data['press_psi'][self._test_data['len']-1], 3))

                    if not collect_data and (current_time % 100) > 50:
                        collect_data = True

                # We can add if statements to run these for different layouts # This could be cleaned up <<<<<<<<<<<<<<<<<<<<<<<<<
                self._timer_checker(test_window, event, values, current_time)


                # Only update plot with accordance to self._plot_update_rate
                if self._plot_update_rate != 1:
                    if (current_time // 100) % self._plot_update_rate == 0 and update_plot:
                        self._plot_checker(test_window, event, values, fig_agg)
                        update_plot=False

                    if not update_plot and (current_time // 100) % self._plot_update_rate != 0:
                        update_plot = True
                else:
                    if (current_time % 100) < 50 and update_plot:
                        self._plot_checker(test_window, event, values, fig_agg)
                        update_plot=False
                    if not update_plot and (current_time % 100) > 50:
                        update_plot = True


            last_time = current_time
            if not run_test or current_time>self._test_duration:
                self.final_window(leak_detected, temp_related, low_pressure)
            continue

        test_window.close()

    # This function will retrieve atmospheric data from the user
    def get_atmospheric_data_usr(self):
        # Will insert getAmbientAirConditions() here with try.
        try:
            mpt.getAmbientAirConditions()
        except:
            while True:
                layout_atm_input = [[sg.Text('Please enter the atmospheric pressure in kPa')],
                         [sg.InputText()],
                         [sg.Submit(), sg.Cancel()]]
                window_atm_input = sg.Window('Atmospheric Data', layout_atm_input)

                event, values = window_atm_input.read()
                window_atm_input.close()

                atm_input = values[0]

                layout_confirmation_window = [[sg.Text('You entered: '+str(atm_input)+' kPa')],
                                                [sg.Submit(), sg.Button('Re-Enter'),sg.Cancel()]]
                confirmation_window= sg.Window('Confirm',  layout_confirmation_window)
                event, values = confirmation_window.read()
                confirmation_window.close()
                if event == 'Submit':
                    return atm_input
                elif event  ==  'Cancel' or event == sg.WIN_CLOSED or event == 'Exit':
                    return -1

    # This function will retrieve information at the end of the test it takes three booleans leak_detected, temp_related, and low_pressure
    def final_window(self, leak_detected=False, temp_related=False, low_pressure=False):
        # Will insert getAmbientAirConditions() here with try.
        while True:
            text=''
            if low_pressure:
                text = "Pressure dropped below the lower bound of "+str(self._pressure_low_bound)+" psi. Repressurize and begin test again."
            if leak_detected and temp_related:
                text =  "Pressure dropped more than "+str(self._leak_tolerance_psi)+" psi. This is likely due to a temperature change. Run again till equilibrium is achieved."
            elif leak_detected:
                text = "Pressure dropped more than "+str(self._leak_tolerance_psi)+" psi. This is likely a real leak. Troubleshoot as necessary"
            else:
                text =  "No leak detected"
            layout_atm_input = [[sg.Text(text)],
                     [sg.Radio('Save data to Excel?', "RADIO1", default=False, key="-SAVE-")],
                     [sg.Button('OK')]]
            window_final_input = sg.Window('Test results', layout_atm_input)

            event, values = window_final_input.read()
            if event == 'OK':
                if values["-SAVE-"]==True: # Currently unfinished need to make many more lists to contain excel data.
                    saveDestination = sg.popup_get_text("Enter file save name (don\'t include \'.xlsx\')")
                    mpt.writeToExcel(saveDestination, self._test_data['press_psi'], self._test_data['press_Pa'], self._test_data['temp_F'],
                                    self._test_data['temp_K'], self._test_data['alPress_psi'], self._test_data['alPress_Pa'], self._test_data['time'],
                                    self._test_data['amb_T_F'], self._test_data['amb_P_Pa'],
                                    np.mean(self._test_data['press_psi']), np.std(self._test_data['press_psi']),
                                    np.mean(self._test_data['press_Pa']), np.std(self._test_data['press_Pa']),
                                    np.mean(self._test_data['alPress_psi']), np.std(self._test_data['alPress_psi']),
                                    np.mean(self._test_data['alPress_Pa']), np.std(self._test_data['alPress_Pa']),
                                    np.mean(self._test_data['temp_K']), np.std(self._test_data['temp_K']),
                                    np.mean(self._test_data['temp_F']), np.std(self._test_data['temp_F']), self._test_data['press_change_psi'],
                                    np.mean(self._test_data['press_change_psi']), np.std(self._test_data['press_change_psi']),
                                    )
                return

            elif event == sg.WIN_CLOSED or event == 'Exit':
                return -1

            atm_input = values[0]



    def run(self):

        #Define the menu  elements
        menu_def= [['File', ['Open', 'Save', 'Exit']],
                    ['Help', 'About...'],]

        #Gui definition
        layout = [
                [sg.Menu(menu_def)],
                [sg.Button('Run Test', font="Times 20", size=(30,1))],
                [sg.Button('Change test settings',font="Times 20",)],
                [sg.Button('Change viewing options',font="Times 20",)],
                [sg.Exit()]]

        window = sg.Window("INL Leak Test", layout, default_element_size=(100,1),
                auto_size_text=False, auto_size_buttons=False, default_button_element_size=(30,1),
                element_justification = "center", font="Helvetica 14", size=(500,200))

        # Loop and process the button menu choices
        while True:
            event,values = window.read()
            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            print('Button = ',event)
            # Process menu choices
            if event== 'About...':
                sg.popup('About this program','Version 1.0', 'PysimpleGUI rocks...')
            elif event== 'Open':
                filename= sg.popup_get_file('file to open', no_window=True)
                print(filename)
            elif event=='Run Test':
                atm_input  = self.get_atmospheric_data_usr()
                self.run_test_window()
