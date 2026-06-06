import os
import pydicom
import pandas as pd
import numpy as np


class DicomModel:

    def __init__(self):
        self.dicom_files = []
        self.volume_3d = None
        self.metadata = {}

    def cargar_carpeta_dicom(self, carpeta):
        archivos = []

        for nombre in os.listdir(carpeta):

            if nombre.endswith(".dcm"):

                ruta = os.path.join(carpeta, nombre)

                dicom = pydicom.dcmread(ruta)

                archivos.append(dicom)

        archivos.sort(
            key=lambda x: int(x.InstanceNumber)
        )

        self.dicom_files = archivos

        self.volume_3d = np.stack(
            [archivo.pixel_array for archivo in archivos]
        )
        

    def extraer_metadata(self):
        dcm = self.dicom_files[0]
        study_time = str(
            dcm.get("StudyTime", "0")
        ).split(".")[0]
        series_time = str(
            dcm.get("SeriesTime", "0")
        ).split(".")[0]

        try:

            study_seconds = (
                int(study_time[0:2]) * 3600 +
                int(study_time[2:4]) * 60 +
                int(study_time[4:6])
            )

            series_seconds = (
                int(series_time[0:2]) * 3600 +
                int(series_time[2:4]) * 60 +
                int(series_time[4:6])
            )

            duracion = series_seconds - study_seconds

        except:

            duracion = 0

        self.metadata = {

            "PatientID":
                dcm.get("PatientID", ""),

            "PatientName":
                str(
                    dcm.get("PatientName", "")
                ),

            "StudyDate":
                dcm.get("StudyDate", ""),

            "StudyTime":
                study_time,

            "Modality":
                dcm.get("Modality", ""),

            "StudyDescription":
                dcm.get("StudyDescription", ""),

            "SeriesTime":
                series_time,

            "DuracionSegundos":
                duracion,

            "Manufacturer":
                dcm.get("Manufacturer", "")
        }

        return self.metadata


    def guardar_csv(self, ruta_csv):
        df = pd.DataFrame([self.metadata])
        df.to_csv(
            ruta_csv,
            index=False)

    def convertir_hu(self):
        dcm = self.dicom_files[0]
        slope = float(
            dcm.get("RescaleSlope", 1))

        intercept = float(
            dcm.get("RescaleIntercept", 0))

        hu = (
            self.volume_3d * slope + intercept)

        return hu