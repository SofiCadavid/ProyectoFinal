import dicom2nifti


class NiftiModel:

    def convertir_dicom_a_nifti(
        self,
        carpeta_dicom,
        carpeta_salida
    ):

        dicom2nifti.convert_directory(
            carpeta_dicom,
            carpeta_salida
        )