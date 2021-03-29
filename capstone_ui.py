from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
import matplotlib, time, sys, pickle
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import PySimpleGUI as sg
import numpy as np
#import mod_press_test1 as mpt

class Pressure_Test_UI:
    def  __init__(self):
        self._small_text_size = 14
        self._large_text_size = 20
        self._font = 'Times '
        self._default_element_size = (30,1)
        self._units = 'us'

        self._display_timer = True
        self._display_PTime_plt = True
        self._display_PTemp_plt = False
        self._display_leak_rate = True
        self._display_TempTime_plt =  False
        self._plot_update_rate = 3
        self._test_data = {'time':[], 'press_psi':[], 'press_Pa':[], 'temp_F':[], 'temp_K':[],'len':0}
        self._test_duration = 15*60
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

    def plt_maker(self, window): # this should be called as a thread, then time.sleep() here would not freeze the GUI
        plt.plot(self._test_data['time'], self._test_data['press_psi'])
        window.write_event_value('-THREAD-', 'done.')
        return plt.gcf()

    def __draw_figure(self, canvas, figure, loc=(0, 0)):
        figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        return figure_canvas_agg


    def __delete_fig_agg(self, fig_agg):
        fig_agg.get_tk_widget().forget()
        plt.close('all')

    def make_plot_layout(self, plot_type='Pressure vs Time'):
        # define the window layout
        plot_layout = [ # [sg.Button('update'), sg.Button('Stop', key="-STOP-"), sg.Button('Exit', key="-EXIT-")],
                  [sg.Radio('Continue Updating', "RADIO1", default=True, size=(12,3),key="-LOOP-"),sg.Radio('Stop Updating', "RADIO1", size=(12,3), key='-NOLOOP-')],
                  [sg.Text(plot_type, font=self._font+str(self._large_text_size))],
                  [sg.Canvas(size=(500,500), key='canvas')]]

        # create the form and show it without the plot
        # plot_window = sg.Window('Demo Application - Embedding Matplotlib In PySimpleGUI',
        #                   plot_layout, finalize=True)

        return plot_layout

    def make_timer_layout(self):
        timer_layout = [[sg.Text('', size=(8,2), font=self._font+str(self._large_text_size), background_color='black', justification='center', key='time')],
                        [sg.Button('Reset')]]

        # timer_window = sg.Window('Running Timer', timer_layout)
        return timer_layout

    def make_text_element(self):
        text_element = [[sg.Text('Test is Running', size=(8,2), font=self._font+ str(self._large_text_size+4), justification='center', key='text output')]
                        ]
        return text_element

    def _plot_checker(self, window, event, values, fig_agg):
        if event == "update":
            if fig_agg is not None:
                    self.delete_fig_agg(fig_agg)
            fig = self.plt_maker(window)
            num+=1
            fig_agg = self.draw_figure(window['canvas'].TKCanvas, fig)

        if event == "-THREAD-":
            print('Acquisition: ', values[event])
            if values['-LOOP-'] == True:
                if fig_agg is not None:
                    self.__delete_fig_agg(fig_agg)
                fig = self.fig_maker(window, num)
                num+=1
                fig_agg = self.__draw_figure(window['canvas'].TKCanvas, fig)
                window.Refresh()

        if event == "-STOP-":
            test_window['-NOLOOP-'].update(True)

    def _timer_checker(self, window, event, values, current_time):
        # --------- Do Button Operations --------
        if event is 'Reset':
            start_time = int(round(time.time() * 100))
            current_time = 0
            paused_time = start_time

        # --------- Display timer in window --------
        window['time'].update('{:02d}:{:02d}.{:02d}'.format((current_time // 100) // 60, (current_time // 100) % 60, current_time % 100), font=self._font+ str(self._large_text_size), background_color='black')

    def _text_updater(self, text, text_color, background_color):
        # --------- Display timer in window --------
        window['text output'].update(text, background_color=background_color, text_color=text_color)

    def run_test_window(self):
        # Calibrate labjack
        mpt.calibrate()

        # Check the true and Falses (NOT IMPLEMENTED) # This could be cleaned up <<<<<<<<<<<<<<<<<<<<<<<<<
        test_layout = self.make_timer_layout()
        test_layout.extend(self.make_plot_layout())

        test_window = sg.Window("Test Window", test_layout, finalize=True)

        start_time = int(round(time.time() * 100))
        last_time = start_time
        fig_agg = None
        data = {}
        while True:
            # Handle window exiting
            event, values = test_window.read()
            if event is None:  # if user closes window
                break
            if event == "-EXIT-":
                break

            current_time = int(round(time.time() * 100)) - start_time
            if current_time < self._test_duration:
                # Fill the test data stored in _test_data. If we want to make it better
                #   we can add average of many samples
                data = mpt.getTestData('us')
                self._test_data['time'].append(current_time)
                self._test_data['press_Pa'].append(data['press_Pa'])
                self._test_data['temp_K'].append(data['temp_K'])
                self._test_data['press_psi'].append(data['press_psi'])
                self._test_data['temp_F'].append(data['temp_F'])
                self._test_data['len']+=1

                pressure_atm_Pa, ambientAirTemperature_F = mpt.getAmbientAirConditions()

                # The following will run similar to leakTestControlLoop # This could be cleaned up <<<<<<<<<<<<<<<<<<<<<<<<<
                leakTestResults, allowablePressure_Pa, allowablePressure_psi, change_in_pressure_psi = \
                    mpt.allowablePressureTest(self._test_data['press_Pa'][0], self._test_data['press_psi'][0],
                        self._test_data['press_psi'][self._test_data['len']], self._test_data['temp_K'][0],
                        self._test_data['temp_K'][self._test_data['len']], pressure_atm_Pa)

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
                        mpt.beepSound(frequency=500, duration=600, numberOfBeeps=10)
                        sleep(1)
                        break

                else:
                    print("Note: \nThe pressure has decreased more that 0.1 psi. "
                          "\nThe pressure decrease was likely due to decreasing temperatures. "
                          "\nContinue running the leak check until thermal equilibrium is achieved.")
                    beepSound(frequency=500, duration=600, numberOfBeeps=5)
                    sleep(1)
                    break

                # We can add if statements to run these for different layouts # This could be cleaned up <<<<<<<<<<<<<<<<<<<<<<<<<
                self.__timer_checker(test_window, event, values, current_time)
                if current_time-last_time > self._plot_update_rate:
                    self.__plot_checker(test_window, event, values, fig_agg)

            last_time = current_time
            continue

        window.close()

    # This function will retrieve atmospheric data from the user
    def get_atmospheric_data_usr(self):
        # Will insert getAmbientAirConditions() here with try.
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
