import pprint

from pyqtgraph.Qt import QtCore
from pyqtgraph.parametertree import *
from PyQt6.QtCore import QSettings, pyqtSlot

#from src.gui.config import *
from .config import *
import ruidaqan
if ruidaqan.DEBUG_MODE:
    from .reader_debug import GetDevicesInfo
else:
    from .reader import GetDevicesInfo


class ParamTreeBase(ParameterTree):
    # ParamTree will output a signal that has the param and the output
    paramChange = QtCore.pyqtSignal(object, object)


    def __init__(self, name, params, reset=False):
        super().__init__()

        self.name = name
        self.settings = QSettings("ruidaqan", self.name)

        self.params = Parameter.create(name=self.name,
                                       type="group",
                                       children=params)

        # load saved data when available or otherwise specified in config.py
        #if self.settings.value("State") != None and not RESET_DEFAULT_PARAMS:
        if self.settings.value("State") != None and not reset:
            self.state = self.settings.value("State")
            self.params.restoreState(self.state)
        else:
            print("Loading default params for", self.name)

        self.setParameters(self.params, showTop=False)
        # When the params change, send to method to emit.
        self.params.sigTreeStateChanged.connect(self.send_change)


    def send_change(self, param, changes):
        self.paramChange.emit(param, changes)


    def get_param_value(self, *childs):
        """Get the current value of a parameter."""
        return self.params.param(*childs).value()


    def set_param_value(self, value, *childs):
        """Set the current value of a parameter."""
        return self.params.param(*childs).setValue(value)


    def set_param_limits(self, value, *childs):
        """Set the limits of a parameter."""
        return self.params.param(*childs).setLimits(value)


    def set_whole_tree(self, method):
        """
        Set properties for the whole tree

        method = "readonly", "writable", "enabled"
        """
        def set_recursive(childs):
            for child in childs:
                if child.hasChildren():
                    set_recursive(child)
                else:
                    if method == "readonly":
                        child.setReadonly()
                    elif method == "writable":
                        child.setWritable()

        set_recursive(self.params.children())


    def save_settings(self):
        self.state = self.params.saveState()
        self.settings.setValue("State", self.state)


    def print(self):
        print(self.name)
        print(self.params)


class GeneralParamTree(ParamTreeBase):
    """
    Configuración de parámetros generales de la medición
    """
    def __init__(self, reset=False):
        _reactores = ["RA-" + str(i) for i in (0, 1, 3, 4, 6, 8, 10)]
        _reactores += ["RP-" + str(i) for i in (0, 10)]

        self.general_settings = [
            {
                "name": "Parámetros generales",
                "type": "group",
                "children": [
                    {
                        "name": "Reactor",
                        "type": "list",
                        "value": "RA-1",
                        "limits": _reactores,
                    },
                    {
                        "name": "Núcleo",
                        "type": "str",
                        "value": " ",
                        "tip": "Núcleo en donde se realiza la medición",
                    },
                    {
                        "name": "Cadenas de medición",
                        "type": "int",
                        "value": 2,
                        "limits": (1, 8),
                        "tip": "Cantidad de detectores para ruido neutrónico",
                    },
                    {
                        "name": "Medición de CIp",
                        "type": "bool",
                        "value": False,
                        "tip": "Adquirir la señal de Ip",
                    },
                    {
                        "name": "Serie",
                        "type": "int",
                        "value": 0,
                        "limits": (0, 1000),
                        "tip": "Identificación del a serie de medición",
                    },
                    {
                        "name": "Comentarios",
                        "type": "text",
                        "value": "",
                        "tip": "Información general sobre la medición",
                    },

                ],
            },
        ]
        super().__init__(name="Config Gral",
                         params=self.general_settings,
                         reset=reset)


class AdvancedParamTree(ParamTreeBase):
    """
    Configuración avanzada

    """


    def __init__(self, n_det=2, cip=True, reset=False):
        self.devices = GetDevicesInfo()
        self.dev_names = self.devices.dev_names
        self.n_det = n_det
        self.cip = cip

        # Lista con los nombres de los canales para dev_names[0]
        ch_n = self.devices.device_info(self.dev_names[0]).channel_names
        # Lista con los rangos para dev_names[0]
        rgs = self.devices.device_info(self.dev_names[0]).ai_ranges

        _cadenas = [
                     {
                         "name": "Cadena " + str(i + 1),
                         "type": "group",
                         "children": [
                             {
                                 "name": "AC",
                                 "type": "group",
                                 "children": [
                                     {
                                         "name": "Canal",
                                         "type": "list",
                                         "value": ch_n[i],
                                         "limits": ch_n,
                                         "tips": "Canal para la componente fluctuante",
                                      },
                                      {
                                         "name": "Rango",
                                         "type": "list",
                                         "value": rgs[-2],
                                         "limits": rgs,
                                         "tips": "Rango para la componente fluctuante",
                                      },
                                      {
                                         "name": "Label",
                                         "type": "str",
                                         "value": f"AC@{i+1}",
                                         "visible": True,
                                      },
                                 ]
                             },
                             {
                                 "name": "DC",
                                 "type": "group",
                                 "children": [
                                     {
                                         "name": "Canal",
                                         "type": "list",
                                         "value": ch_n[n_det + i],
                                         "limits": ch_n,
                                         "tips": "Canal para la componente continua",
                                      },
                                      {
                                         "name": "Rango",
                                         "type": "list",
                                         "value": rgs[-1],
                                         "limits": rgs,
                                         "tips": "Canal para la componente fluctuante",
                                      },
                                      {
                                         "name": "Label",
                                         "type": "str",
                                         "value": f"DC@{i+1}",
                                         "visible": True,
                                      },
                                 ]
                             },
                             {
                                 "name": "AC filtro",
                                 "type": "group",
                                 "children": [
                                     {
                                         "name": "Canal",
                                         "type": "list",
                                         "value": ch_n[n_det*2 + i],
                                         "limits": ch_n,
                                         "tips": "Canal para monitoreo del filtro anti-aliasing"
                                     },
                                     {
                                         "name": "Rango",
                                         "type": "list",
                                         "value": rgs[-2],
                                         "limits": rgs,
                                         "tips": "Canal para la componente fluctuante",
                                     },
                                     {
                                         "name": "Label",
                                         "type": "str",
                                         "value": f"AC_filt@{i+1}",
                                         "visible": True,
                                      },
                                 ]
                             },
                         ]
                     } for i in range(n_det)
                   ]

        if self.cip:
            _cadenas.append(
               {
                   "name":  "Cadena CIp",
                   "type": "group",
                   "children": [
                       {
                           "name": "DC",
                           "type": "group",
                           "children": [
                               {
                                  "name": "Canal",
                                  "type": "list",
                                  "value": ch_n[n_det*3],
                                  "limits": ch_n,
                                  "tips": "CAnal para adquirir la señal de CIp",
                               },
                               {
                                  "name": "Rango",
                                  "type": "list",
                                  "value": rgs[-1],
                                  "limits": rgs,
                                  "tips": "CAnal para adquirir la señal de CIp",
                               },
                               {
                                  "name": "Label",
                                  "type": "str",
                                  "value": f"DC_Ip",
                                  "visible": True,
                               },
                           ]
                       }
                   ]
               }
            )

        self.advanced_settings = [
            {
                "name": "Configuración avanzada",
                "type": "group",
                "children": [
                    {
                        "name": "Dispositivo",
                        "type": "list",
                        'value': self.dev_names[0],
                        'limits': self.dev_names,

                    },
                    *_cadenas,
                ],
            },
        ]

        super().__init__(name="Config Avanzada",
                         params=self.advanced_settings,
                         reset=reset)


    def actualiza_cadenas_med(self, nuevas_cadenas):
        """
        Se aagregan o quitan cadenas de medición
        """
        dev = self.get_param_value("Configuración avanzada", "Dispositivo")
        ch_n = self.devices.device_info(dev).channel_names
        rgs = self.devices.device_info(dev).ai_ranges

        if nuevas_cadenas > self.n_det:
            # Agrego canales luego de los existentes
            for _ in range(nuevas_cadenas - self.n_det):
                self.params.param("Configuración avanzada").insertChild(
                        1 + self.n_det,
                    {
                         "name": "Cadena " + str(self.n_det + 1),
                         "type": "group",
                         "children": [
                             {
                                 "name": "AC",
                                 "type": "group",
                                 "children": [
                                     {
                                         "name": "Canal",
                                         "type": "list",
                                         "value": ch_n[self.n_det],
                                         "limits": ch_n,
                                         "tips": "Canal para la componente fluctuante",
                                      },
                                      {
                                         "name": "Rango",
                                         "type": "list",
                                         "value": rgs[-2],
                                         "limits": rgs,
                                         "tips": "Rango para la componente fluctuante",
                                      },
                                      {
                                         "name": "Label",
                                         "type": "str",
                                         "value": f"AC@{self.n_det + 1}",
                                         "visible": True,
                                      },

                                 ]
                             },
                             {
                                 "name": "DC",
                                 "type": "group",
                                 "children": [
                                     {
                                         "name": "Canal",
                                         "type": "list",
                                         "value": ch_n[self.n_det * 2 + 1],
                                         "limits": ch_n,
                                         "tips": "Canal para la componente continua",
                                      },
                                      {
                                         "name": "Rango",
                                         "type": "list",
                                         "value": rgs[-1],
                                         "limits": rgs,
                                         "tips": "Canal para la componente fluctuante",
                                      },
                                      {
                                         "name": "Label",
                                         "type": "str",
                                         "value": f"DC@{self.n_det + 1}",
                                         "visible": True,
                                      },

                                 ]
                             },
                             {
                                 "name": "AC filtro",
                                 "type": "group",
                                 "children": [
                                     {
                                         "name": "Canal",
                                         "type": "list",
                                         "value": ch_n[self.n_det * 3 + 2],
                                         "limits": ch_n,
                                         "tips": "Canal para monitoreo del filtro anti-aliasing"
                                     },
                                     {
                                         "name": "Rango",
                                         "type": "list",
                                         "value": rgs[-2],
                                         "limits": rgs,
                                         "tips": "Canal para la componente fluctuante",
                                     },
                                     {
                                         "name": "Label",
                                         "type": "str",
                                         "value": f"AC_filt@{self.n_det + 1}",
                                         "visible": True,
                                      },
                                 ]
                             },
                         ]
                     }
                )
                self.n_det += 1
        else:
            for _ in range(self.n_det - nuevas_cadenas):
                self.params.param("Configuración avanzada",
                        "Cadena " + str(self.n_det)).remove()
                self.n_det -= 1
        self.set_channels_names()


    def actualiza_cip(self):
        dev = self.get_param_value("Configuración avanzada", "Dispositivo")
        ch_n = self.devices.device_info(dev).channel_names
        rgs = self.devices.device_info(dev).ai_ranges

        _childs = self.params.param("Configuración avanzada").children()
        _child_name = [_child.name() for _child in _childs]
        if "Cadena CIp" in _child_name:
            self.params.param("Configuración avanzada",
                               "Cadena CIp").remove()
        else:
            self.params.param("Configuración avanzada").insertChild(self.n_det + 1,
                {
                    "name":  "Cadena CIp",
                    "type": "group",
                    "children": [
                        {
                            "name": "DC",
                            "type": "group",
                            "children": [
                                {
                                   "name": "Canal",
                                   "type": "list",
                                   "value": ch_n[self.n_det*3],
                                   "limits": ch_n,
                                   "tips": "CAnal para adquirir la señal de CIp",
                                },
                                {
                                   "name": "Rango",
                                   "type": "list",
                                   "value": rgs[-1],
                                   "limits": rgs,
                                   "tips": "CAnal para adquirir la señal de CIp",
                                },
                                {
                                   "name": "Label",
                                   "type": "str",
                                   "value": f"DC_Ip",
                                   "visible": True,
                                },
                            ]
                        }
                    ]
                }
             )
        self.cip = not self.cip


    def get_channels_labels(self):
        """
        Devuelve los labels para cada canal

        [Cadena1.AC  Cadena1.DC  Cadena1.AC_filtro  Cadena2.AC ... Cadena.CIp]
        """
        lbls = []
        for i in range(self.n_det):
            for tipo in ["AC", "DC", "AC filtro"]:
                lbls.append(self.get_param_value("Configuración avanzada",
                                                 "Cadena " + str(i + 1),
                                                  tipo, "Label"))
        if self.cip:
            lbls.append(self.get_param_value( "Configuración avanzada",
                                              "Cadena CIp", "DC",
                                              "Label"))

        return lbls


    def get_channels_ranges(self):
        """
        Devuelve los rangos para cada canal

        [Cadena1.AC  Cadena1.DC  Cadena1.AC_filtro  Cadena2.AC ... Cadena.CIp]
        """
        rngs = []
        for i in range(self.n_det):
            for tipo in ["AC", "DC", "AC filtro"]:
                rngs.append(self.get_param_value("Configuración avanzada",
                                                 "Cadena " + str(i + 1),
                                                  tipo, "Rango"))
        if self.cip:
            rngs.append(self.get_param_value( "Configuración avanzada",
                                              "Cadena CIp", "DC",
                                              "Rango"))

        return rngs


    def set_channels_ranges(self, ranges):
        """
        Setea los rangos para cada canal

        El orden de "Values" debe ser
        [Cadena1.AC  Cadena1.DC  Cadena1.AC_filtro  Cadena2.AC ... Cadena.CIp]

        Cada elemento debe ser una tupla (min, max). Ejemplo: (-10, 10)
        """
        k = 0
        for i in range(self.n_det):
            for tipo in ["AC", "DC", "AC filtro"]:
                self.set_param_value(ranges[k], "Configuración avanzada",
                                                "Cadena " + str(i + 1), tipo,
                                                "Rango")
                k += 1

        if self.cip:
            self.set_param_value(ranges[-1], "Configuración avanzada",
                                             "Cadena CIp", "DC", "Rango")


    def set_channels_range_limits(self, limits):
        """
        Aplica "limits" a los rangos de todos los canales. El mismo para todos.
        """
        cadenas = ["Cadena " + str(i + 1) for i in range(self.n_det)]

        for cadena in cadenas:
            for tipo in ["AC", "DC", "AC filtro"]:
                self.set_param_limits(limits, "Configuración avanzada",
                                                      cadena,
                                                      tipo,
                                                      "Rango"
                                                      )
        if self.cip:
            self.set_param_limits(limits, "Configuración avanzada",
                                                 "Cadena CIp",
                                                 "DC",
                                                 "Rango"
                                                 )


    def get_ADC_ranges(self):
        dev = self.get_param_value("Configuración avanzada", "Dispositivo")
        return self.devices.device_info(dev).ai_ranges


    def get_ADC_resolution(self):
        dev = self.get_param_value("Configuración avanzada", "Dispositivo")
        return self.devices.device_info(dev).resolution_ADC


    def get_channels_coefs(self, channels, ranges):
        """
        Devuelve los coeficientes de la calibración para pasar de raw a voltaje

        [Cadena1.AC  Cadena1.DC  Cadena1.AC_filtro  Cadena2.AC ... Cadena.CIp]
        """

        dev = self.get_param_value("Configuración avanzada", "Dispositivo")
        _dev_info = self.devices.device_info(dev)
        coef = []
        for ch, rg in zip(channels, ranges):
            coef.append(_dev_info.scaling_coeff(ch, rg))

        return coef


    def update_device(self, new_dev):
        """
        Reemplaza el dispositivo en todos los canales
        """
        old_chan_suff = [a.split('/')[1] for a in self.get_channels()]
        new_chan = [new_dev + '/' + ch for ch in old_chan_suff]
        # Cambio los límites de cada canal
        new_limits = self.devices.device_info(new_dev).channel_names
        self.set_channels_limits(new_limits)
        # Cambio los valores de cada canal
        self.set_channels_names(new_chan)
        # Copio los rangos previos al cambio
        old_rngs = self.get_channels_ranges()
        # Actualiza los limits de los rangos de cada canal
        rgs = self.devices.device_info(new_dev).ai_ranges
        self.set_channels_range_limits(rgs)
        # Trata de poner los mismos rangos que había (puede que no sea posible
        # siempre, en tal caso queda el primero de la lista nueva)
        self.set_channels_ranges(old_rngs)


    def set_channels_limits(self, limits):
        """
        Aplica "limits" a los limits de todos los canales. El mismo para todos.
        """
        cadenas = ["Cadena " + str(i + 1) for i in range(self.n_det)]

        for cadena in cadenas:
            for tipo in ["AC", "DC", "AC filtro"]:
                self.set_param_limits(limits, "Configuración avanzada",
                                                      cadena,
                                                      tipo,
                                                      "Canal"
                                                      )
        if self.cip:
            self.set_param_limits(limits, "Configuración avanzada",
                                                 "Cadena CIp",
                                                 "DC",
                                                 "Canal"
                                                 )


    def get_channels(self, tipos=None):
        """
        Devuelve los canales utilizados para la adquisició

        Se puede especifica el tipo de canal que se quiere leer. Si tipos =
        None devuelve todos los canales

        Ordenados por cadena y por tipo:
            [ Cadena1(AC) Cadena1(DC) Cadena1(AC filtro) Cadena2(AC)
            ...CadenaCIp(DC) ]

        tipo: string or list of string ['AC', 'DC', 'AC filtro']

        """
        cadenas = ["Cadena " + str(i + 1) for i in range(self.n_det)]

        if tipos is None:
            _tipos = ['AC', 'DC', 'AC filtro']
        else:
            _tipos = [tipos] if isinstance(tipos, str) else tipos

        channels = []
        for cadena in cadenas:
            for tipo in _tipos:
                channels.append(self.get_param_value("Configuración avanzada",
                                                      cadena,
                                                      tipo,
                                                      "Canal"
                                                      )
                                                    )
        if self.cip and 'DC' in _tipos:
            channels.append(self.get_param_value("Configuración avanzada",
                                                 "Cadena CIp",
                                                 "DC",
                                                 "Canal"
                                                 )
                                              )
        return channels


    def set_channels_names(self, new_names=None):
        """
        Escribe los valores de los canales

        Si new_names == None, se elige un orden por default (polémtico). De lo
        contrario se usa new_names

        TODO: chequear que coincidan tamaños entre new_names y los canales
        """
        dev = self.get_param_value("Configuración avanzada", "Dispositivo")
        # Esta es una fomra posible de hacer la conexiones
        # no es la misma que se utiliza en la actualidad
        if new_names is None:
            # Valores por default
            chan_num = []
            for i in range(self.n_det):
                for j in range(3):
                    chan_num.append(self.n_det*j + i)

            if self.cip: chan_num.append(self.n_det*3)
            value = [dev + '/ai' + str(i) for i in chan_num]
        else:
            value = new_names

        k = 0
        for i in range(self.n_det):
            for tipo in ['AC', 'DC', 'AC filtro']:
                self.set_param_value(value[k], "Configuración avanzada",
                                     "Cadena " + str(i+1), tipo, "Canal")
                k += 1
        if self.cip:
            self.set_param_value(value[-1], "Configuración avanzada",
                                 "Cadena CIp", "DC", "Canal")


    def get_DC_channels(self):
        """"
        Devuelve los canales utilizados para medir las DC's
        """
        cadenas = ["Cadena " + str(i + 1) for i in range(self.n_det)]
        if self.cip: cadenas.append("Cadena CIp")

        channels = [self.get_param_value("Configuración avanzada", cad,
                                        "DC", "Canal") for cad in cadenas ]

        return channels


class EspMedParamTree(ParamTreeBase):
    """
    Configuración de parámetros específicoss a una dada medición
    """
    def __init__(self, n_det=2, cip=True, reset=False):
        self.n_det = n_det
        self.cip = cip

        _cadenas = [
            {
                "name": "Cadena " + str(i + 1),
                "type": "group",
                "children": [
                    {
                        "name": "Sensibilidad",
                        "type": "group",
                        "children": [
                            {
                                "name": "Rango",
                                "type": "list",
                                "value": 1e-9,
                                "limits": {
                                    "[1] 1E-9 A/V": 1e-9,
                                    "[2] 1E-8 A/V": 1e-8,
                                    "[3] 1E-7 A/V": 1e-7,
                                    "[4] 1E-6 A/V": 1e-6,
                                    "[5] 1E-5 A/V": 1e-5,
                                    "[6] 1E-4 A/V": 1e-4,
                                    "Otro": None,
                                    },
                                "tip": "Rango del amplificador",
                                "suffix": "A/V",
                            },
                            {
                                "name": "Multiplicador",
                                "type": "list",
                                "value": 1,
                                "limits": {'x1': 1, 'x3': 3},
                                "tip": "Factor de multiplicación",
                                "visible": True
                            },
                            {
                                "name": "Manual",
                                "type": "float",
                                "value": 1e-9,
                                "limits": (0, 1e3),
                                "tip": "Ingresar sensibilidad manualmente",
                                "suffix": "A/V",
                                "visible": False,
                            },

                        ]
                    },
                    {
                        "name": "Ganancia AC",
                        "type": "list",
                        "value": 100,
                        "limits": [100, 200, 400, 600, 800],
                        "tip": "Ganancia de la AC",
                    },
                    {
                        "name": "Offset",
                        "type": "float",
                        "value": 0,
                        "suffix": "V",
                        "tip": "Offset del amplificador",
                    },
                    {
                        # TODO: Sacarlo de acá, dejar el general. Queda
                        # mientras se prueba escribir el .RUI
                        # Estos comentarios deben estar en los generales de la
                        # medición
                        "name": "Comentario",
                        "type": "text",
                        "value": "Ubicación detector " + str(i + 1) + ": ",
                        "tip": "Comentario para .RUI",
                        "visible": True,
                        "expanded": False,
                    },

                ]
           } for i in range(self.n_det)
        ]
        if self.cip:
            _cadenas.append(
                {
                    "name": "Cadena CIp",
                    "type": "group",
                    "children": [
                        {
                            "name": "Sensibilidad",
                            "type": "float",
                            "value": 0.25 * 1e-9,
                            "tip": "Rango del amplificador de CIp",
                            'suffix': "A/V"
                        },
                        {
                            "name": "Offset",
                            "type": "float",
                            "value": 0.5,
                            "suffix": "V",
                            "tip": "Offset del amplificador",
                        },
                    ]
                }
            )


        self.specific_settings = [
            {
                "name": "Parámetros medición",
                "type": "group",
                "children": [
                    *_cadenas,
                    {   "name": "DAQ",
                        "type": "group",
                        "children": [
                             {
                             'name': "BW",
                             'type': 'list',
                             "limits": {'40 Hz': 40,
                                        '200 Hz': 200,
                                         'Otro': None},
                             'value': 200,
                             "suffix": "Hz",
                             "tip": "Ancho de banda (fs = 2BW)"
                             },
                            {
                                "name": "BW manual",
                                "type": "float",
                                "value": 200,
                                "suffix": 'Hz',
                                "visible": False,
                                "tip": "Ancho de banda (fs = 2BW)"
                            },
                            {
                                "name": "Puntos",
                                "type": "int",
                                "value": 512,
                                "limits": (1, 4104304),
                                "tip": "Número de puntos por historia",
                            },
                            {
                                "name": "Historias",
                                "type": "int",
                                "value": 100,
                                "limits": (1, 1000000),
                                "tip": "Número de historias",
                            },

                        ]
                    },
                    {   "name": "Medición",
                        "type": "group",
                        "children": [
                            {
                                "name": "Nivel",
                                "type": "int",
                                "value": 1,
                                "limits": (1, 1000),
                                "tip": "Identificador del nivel actual",
                            },
                            {
                                "name": "Medición",
                                "type": "int",
                                "value": 1,
                                "limits": (1, 1000),
                                "tip": "Identificador de la medición actual",
                            },
                            {
                                "name": "Comentario",
                                "type": "text",
                                "value": "BC1: \nBC2: \nBC3: \nBC4: ",
                                "tip": "Comentario sobre la medición actual",
                            },

                        ]
                    },

                ],
            },
        ]
        super().__init__(name="Config Espec",
                         params=self.specific_settings,
                         reset=reset)

        # Mantiene actualizada sensibilidad manual
        self.paramChange.connect(self._sensib_manual)
        # Mantiene actualizad BW manual
        self.params.param("Parámetros medición", "DAQ", "BW"
                                    ).sigValueChanged.connect(self._bw_manual)


    @pyqtSlot(object, object)
    def _bw_manual(self, _, change):
        """ Actualiz BW manual """
        _path = ("Parámetros medición", "DAQ", "BW manual")
        if change is None:
            self.params.param(*_path).show()
        else:
            # Pasa el valor a BW manual (la que se lee siempre)
            self.set_param_value(change, *_path)
            self.params.param(*_path).hide()


    @pyqtSlot(object, object)
    def _sensib_manual(self, _, changes):
        """
        En ("Sensibilidad, Manual") se escribe siempore el producto del rango
        por el multiplicador. Es el valor que se leerá para convertir a
        corriente.

        Se mantiene (Sensiblidad, Manual) actualizado ante cambios en rango y
        multiplicador.
        """

        for param, change, data in changes:
            _childs = self.params.childPath(param)
            if _childs:
                if "Rango" in _childs and change == "value":
                    _parent = self.params.param(*_childs).parent()
                    _parent_path = self.params.childPath(_parent)
                    _man_child = _parent_path + ["Manual"]
                    _mult_child = _parent_path + ["Multiplicador"]
                    if data is None:
                        self.params.param(*_man_child).show()
                        # Se esconden multiplicador y se muestra sensibilidad
                        self.params.param(*_man_child).show()
                        self.params.param(*_mult_child).hide()
                    else:
                        # Lee el valor del multiplicador
                        _mult_path = _parent_path + ["Multiplicador"]
                        _mult = self.get_param_value(*_mult_path)
                        # Escribe el valor de la sensibilidad
                        self.set_param_value(data * _mult, *_man_child)
                        # Se esconde ingreso manual y se muestra multiplicador
                        self.params.param(*_man_child).hide()
                        self.params.param(*_mult_child).show()
                elif "Multiplicador" in _childs and change == 'value':
                    # Lee el valor del rango
                    _parent = self.params.param(*_childs).parent()
                    _parent_path = self.params.childPath(_parent)
                    _sens_child = _parent_path + ["Rango"]
                    _sens = self.get_param_value(*_sens_child)
                    # Escribe el valor de la sensibilidad
                    _man_child = _parent_path + ["Manual"]
                    self.set_param_value(data * _sens, *_man_child)


    def get_sensitivities(self):
        """
        Devuelve las sensibilidades de los amplificadores utilizadas para cada
        cadena

        Ordenados por cadena:
            [ Sensibilidad_1 Sensibilidad_2 .... Sensibilidad_CIp]

        """
        cadenas = ["Cadena " + str(i + 1) for i in range(self.n_det)]

        sens = []
        for cadena in cadenas:
            sens.append(self.get_param_value("Parámetros medición",
                                              cadena,
                                              "Sensibilidad",
                                              "Manual",
                                              )
                        )
        if self.cip:
            sens.append(self.get_param_value("Parámetros medición",
                                             "Cadena CIp",
                                             "Sensibilidad",
                                              )
                        )
        return sens


    def get_AC_gains(self):
        """
        Devuelve la ganancia de la componente AC de cada cadena

        Ordenados por cadena:
            [AC_gain_1  AC_gain_2 ....]
        """
        cadenas = ["Cadena " + str(i + 1) for i in range(self.n_det)]

        ac_gains = []
        for cadena in cadenas:
            ac_gains.append(self.get_param_value("Parámetros medición",
                                                 cadena,
                                                 "Ganancia AC",
                                                 )
                           )
        return ac_gains


    def hide_AC_gains(self):
        """
        Oculta el parámetro AC_gain de todas las cadenas

        Ordenados por cadena:
            [AC_gain_1  AC_gain_2 ....]
        """
        cadenas = ["Cadena " + str(i + 1) for i in range(self.n_det)]

        ac_gains = []
        for cadena in cadenas:
            self.params.param("Parámetros medición", cadena,
                    "Ganancia AC").hide()
        return None


    def get_offsets(self):
        """
        Devuelve los offsets de los amplificadores utilizadas para cada cadena

        Ordenados por cadena:
            [ Offset_1 Offset_2 .... Offset_CIp]]
        """

        cadenas = ["Cadena " + str(i + 1) for i in range(self.n_det)]

        offsets = []
        for cadena in cadenas:
            offsets.append(self.get_param_value("Parámetros medición",
                                                cadena,
                                                "Offset",
                                                )
                           )
        if self.cip:
            offsets.append(self.get_param_value("Parámetros medición",
                                                "Cadena CIp",
                                                "Offset",
                                                )
                          )
        return offsets


    def get_comments(self):
        """
        Devuelve los comentarios para cada cadena de medición

        Ordenados por cadena:
            [ comment_1 comment_2 ...]
        """
        cadenas = ["Cadena " + str(i + 1) for i in range(self.n_det)]
        comments = []
        for cadena in cadenas:
            comments.append(self.get_param_value("Parámetros medición",
                                                 cadena,
                                                 "Comentario",
                                                 )
                            )
        return comments


class OscilloscopeParamTree(ParamTreeBase):
    """
    Configuración de parámetros generales de la medición
    """
    def __init__(self, n_chan=1, reset=False):
        self._n_chan = n_chan
        self.devices = GetDevicesInfo()
        dev_names = self.devices.dev_names
        dev = dev_names[0]

        self._dev_names = dev_names

        # Lista con los nombres de los canales para dev_names[0]
        self._ch_n = self.devices.device_info(dev).channel_names
        # Lista con los rangos para dev_names[0]
        self._rgs = self.devices.device_info(dev).ai_ranges

        canales = [
                    {
                        "name": "Canal " + str(i),
                        "type": "group",
                        "children": [
                            {
                                "name": "Nombre",
                                "type": "list",
                                "value": self._ch_n[i],
                                "limits": self._ch_n,
                            },
                            {
                                "name": "Rango",
                                "type": "list",
                                "value": self._rgs[-1],
                                "limits": self._rgs,
                            },
                            {
                                "name": "Color",
                                "type": "color",
                                "value": (i, 6),
                            },
                            {
                                "name": "Identificación",
                                "type": "str",
                                "value": "Canal " + str(i),
                            },


                       ]
                    } for i in range(n_chan)
                  ]

        self.osc_settings = [
            {
                "name": "Configuración",
                "type": "group",
                "children": [
                    {
                        "name": "Cantidad de canales",
                        "type": "list",
                        "value": 2,
                        "limits": [i for i in range(1, len(self._ch_n) + 1)],
                    },
                    {
                        "name": "Dispositivo",
                        "type": "list",
                        "value": dev,
                        "limits": self._dev_names,
                    },
                    {
                        "name": "Frecuencia",
                        "type": "float",
                        "value": 1000,
                        "limits": (0, 1e9),
                        "suffix": "Hz",
                    },
                    {
                        "name": "Datos lectura",
                        "type": "int",
                        "value": 200,
                        "limits": (0, 1e9),
                    },
                    {
                        "name": "Datos buffer",
                        "type": "int",
                        "value": 100,
                        "limits": (0, 1e9),
                        "visible": False,
                    },
                    *canales,

                ],
            },
        ]
        super().__init__(name="Config osciloscopio",
                         params=self.osc_settings,
                         reset=reset)
        self.device = dev


    @property
    def device(self):
        return self._device


    @device.setter
    def device(self, new_dev):
        self._device = new_dev
        # Cambio los valores de cada canal
        old_chan_suff = [a.split('/')[1] for a in self.get_channels()]
        new_chan = [new_dev + '/' + ch for ch in old_chan_suff]
        self.set_channels_names(new_chan)
        # Cambio los límites de cada canal
        self._ch_n = self.devices.device_info(new_dev).channel_names
        self.set_channels_limits(self._ch_n)
        self._rgs = self.devices.device_info(new_dev).ai_ranges


    def actualizar_numero_canales(self, nuevos_canales):
        if nuevos_canales > self._n_chan:
            # Agrego canales luego de los existentes
            for _ in range(nuevos_canales - self._n_chan):
                self.params.param(
                        "Configuración").insertChild(5 + self._n_chan,
                                {
                                    "name": "Canal " + str(self._n_chan) ,
                                    "type": "group",
                                    "children": [
                                        {
                                            "name": "Nombre",
                                            "type": "list",
                                            "value": self._ch_n[self._n_chan],
                                            "limits": self._ch_n,
                                        },
                                        {
                                            "name": "Rango",
                                            "type": "list",
                                            "value": self._rgs[-1],
                                            "limits": self._rgs,
                                        },
                                        {
                                            "name": "Color",
                                            "type": "color",
                                            "value": (self._n_chan, 5),
                                        },
                                        {
                                            "name": "Identificación",
                                            "type": "str",
                                            "value": "Canal " + str(self._n_chan),
                                        },

                                    ]
                                 }
                             )
                self._n_chan += 1
        else:
            # Quito canales
            for _ in range(self._n_chan - nuevos_canales):
                self._n_chan -= 1
                self.params.param("Configuración",
                        "Canal " + str(self._n_chan)).remove()


    def get_channels(self):
        """
        Devuelve los canales utilizados para la adquisición
        """
        channels = [self.get_param_value(
                                         "Configuración",
                                         "Canal " + str(i),
                                         "Nombre",
                                         ) for i in range(self._n_chan)
                                    ]
        return channels


    def get_colors(self):
        """
        Devuelve los colores utilizados para cada canal
        """
        colores = [self.get_param_value(
                                         "Configuración",
                                         "Canal " + str(i),
                                         "Color",
                                         ) for i in range(self._n_chan)
                                    ]
        return colores


    def get_names(self):
        """
        Devuelve los nombres utilizados para cada canal
        """
        nombres = [self.get_param_value(
                                         "Configuración",
                                         "Canal " + str(i),
                                         "Identificación",
                                         ) for i in range(self._n_chan)
                                    ]
        return nombres


    def get_ranges(self):
        """
        Devuelve los rangos utilizados para cada canal
        """
        rangos = [self.get_param_value(
                                         "Configuración",
                                         "Canal " + str(i),
                                         "Rango",
                                         ) for i in range(self._n_chan)
                                    ]
        return rangos


    def set_channels_names(self, new_names=None):
        """
        Escribe los valores de los canales
        """
        channels = [self.set_param_value(new_names[i],
                                         "Configuración",
                                         "Canal " + str(i),
                                         "Nombre",
                                         ) for i in range(self._n_chan)
                                    ]
        return channels


    def set_channels_limits(self, new_names=None):
        """
        Escribe los valores de los canales
        """
        channels = [self.set_param_limits(new_names,
                                         "Configuración",
                                         "Canal " + str(i),
                                         "Nombre",
                                         ) for i in range(self._n_chan)
                                    ]
        return channels


if __name__ == "__main__":
    pass
