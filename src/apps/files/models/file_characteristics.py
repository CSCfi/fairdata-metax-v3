# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import SystemCreatorBaseModel
from apps.refdata import models as refdata
from apps.refdata.models import ConceptProxyMixin


class FileFormatVersion(ConceptProxyMixin, refdata.FileFormatVersion):
    """File format version."""


class FileCharacteristics(SystemCreatorBaseModel):
    class CSVDelimiterChoices(models.TextChoices):
        TAB = "\t", "Tab"
        SPACE = " ", "Space"
        SEMICOLON = ";", "Semicolon"
        COMMA = ",", "Comma"
        COLON = ":", "Colon"
        PERIOD = ".", "Period"
        PIPE = "|", "Pipe"

    class CSVRecordSeparatorChoices(models.TextChoices):
        LF = "LF", "LF"
        CR = "CR", "CR"
        CRLF = "CRLF", "CRLF"

    class EncodingChoices(models.TextChoices):
        UTF_8 = "UTF-8", "UTF-8"
        UTF_16 = "UTF-16", "UTF-16"
        UTF_32 = "UTF-32", "UTF-32"
        ISO_8859_15 = "ISO-8859-15", "ISO-8859-15"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_format_version = models.ForeignKey(
        FileFormatVersion,
        related_name="file_characteristics",
        on_delete=models.SET_NULL,
        null=True,
    )
    encoding = models.CharField(
        max_length=64, choices=EncodingChoices.choices, blank=True, null=True
    )
    csv_has_header = models.BooleanField(blank=True, null=True)
    csv_quoting_char = models.CharField(max_length=8, blank=True, null=True)
    csv_delimiter = models.CharField(
        max_length=8, choices=CSVDelimiterChoices.choices, blank=True, null=True
    )
    csv_record_separator = models.CharField(
        max_length=8, choices=CSVRecordSeparatorChoices.choices, blank=True, null=True
    )

    class Meta:
        ordering = ["id"]

    def to_legacy(self):
        val = {}
        if fmt := self.file_format_version:
            val["file_format"] = fmt.file_format
            val["format_version"] = fmt.format_version
        if self.encoding:
            val["encoding"] = self.encoding
        if self.csv_record_separator:
            val["csv_record_separator"] = self.csv_record_separator
        if self.csv_has_header is not None:
            val["csv_has_header"] = self.csv_has_header
        if self.csv_quoting_char:
            val["csv_quoting_char"] = self.csv_quoting_char
        if self.csv_delimiter:
            val["csv_delimiter"] = self.csv_delimiter
        if self.csv_record_separator:
            val["csv_record_separator"] = self.csv_record_separator
        return val
