class Printing:
    def __init__(self, parameters):
        self.parameters = parameters

    def startProcess(self):
        print("Printing Process Started")

class CustomerCopy:
    def __init__(self, parameters):
        self.parameters = parameters

    def startProcess(self):
        print("Customer Copy Process Started")

class LabelAutomationClass:
    def __init__(self, processName, zipFile):
        self.processName = processName
        self.zipFile = zipFile

        if self.processName == 'customer_approval':
            self.__class__ = CustomerCopy
        else:
            self.__class__ = Printing

        # Initialize the new base class directly.
        self.__init__(zipFile)

# Create instance with processName parameter
automation = LabelAutomationClass(processName='customer_approval', zipFile='some_parameters')
automation.startProcess()
