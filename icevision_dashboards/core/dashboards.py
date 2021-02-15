# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/core.dashboards.ipynb (unless otherwise specified).

__all__ = ['Dashboard', 'Gallery', 'DatasetOverview', 'MultiDatasetOverview', 'DatasetComparison', 'DatasetFilter',
           'DatasetFilterWithRangeSliderAndMultiSelect', 'ScatterDatasetFilter', 'DatasetGenerator']

# Cell
from typing import List, Union, Optional
from abc import ABC, abstractmethod
from math import floor, ceil
import os

import numpy as np
import pandas as pd
import panel as pn
import panel.widgets as pnw

from ..plotting import *
from .data import *

# Cell
class Dashboard(ABC):
    def __init__(self, width: int = 500, height: int = 500):
        self.width = width
        self.height = height
        self.build_gui()

    @abstractmethod
    def show(self):
        pass

    @abstractmethod
    def build_gui(self):
        pass

# Cell
class Gallery(Dashboard):
    def __init__(self, dataset, gallery_desciptor, img_id_col, sort_cols=None, width=500, height=500):
        """The dataset need to have a property num_images."""
        self.dataset = dataset
        self.sort_cols = sort_cols
        self.gallery_desciptor = gallery_desciptor
        self.img_id_col = img_id_col
        self.num_images = getattr(self.dataset, self.gallery_desciptor).sort_values(img_id_col).drop_duplicates(self.img_id_col).shape[0]
        self.UPDATING = False
        if sort_cols is None:
            self.index_mapping = getattr(self.dataset, self.gallery_desciptor).sort_values(img_id_col).drop_duplicates(self.img_id_col).reset_index(drop=True)
        else:
            self.index_mapping = getattr(self.dataset, self.gallery_desciptor).sort_values(sort_cols[0]).drop_duplicates(self.img_id_col).reset_index(drop=True)
        super().__init__(width, height)

    def get_image_by_index(self, index):
        height_subtracor = 50 if self.sort_cols is None else 100
        return self.dataset.get_image_by_image_id(self.index_mapping.iloc[index][self.img_id_col], width=self.width, height=self.height-height_subtracor)

    def update_sorting(self, event):
        sort_ascending = False if  "Desc." in self.sort_order.value else True
        data = getattr(self.dataset, self.gallery_desciptor).sort_values(self.sorter.value, ascending=sort_ascending)
        if "Drop duplicates" in self.sort_order.value:
            data = data.drop_duplicates(self.img_id_col)
        self.num_images = data.shape[0]
        self.image_count = pn.Row("/" + str(self.num_images), width=int(self.width/6))
        self.gui[0][1][2] = self.image_count
        self.index_mapping = data.reset_index(drop=True)

    def build_gui(self):
        if self.sort_cols is not None:
            self.sorter = pnw.Select(name="Sort by", options=self.sort_cols)
            self.sorter.param.watch(self.update_sorting, "value")
            self.sort_order = pnw.CheckButtonGroup(name="Options", options=["Desc.", "Drop duplicates"])
            self.sort_order.param.watch(self.update_sorting, "value")
            self.sort_gui = pn.Row(self.sorter, self.sort_order)

        self.btn_prev = pnw.Button(name="<", width=int(2*self.width/6))
        self.btn_next = pnw.Button(name=">", width=int(2*self.width/6))
        self.current = pnw.TextInput(value="1", width=int(self.width/6))
        self.image_count = pn.Row("/" + str(self.num_images), width=int(self.width/6))
        if self.sort_cols is not None:
            self.gui_controlls = pn.Column(self.sort_gui, pn.Row(self.btn_prev, self.current, self.image_count, self.btn_next, align="center", height=50))
        else:
            self.gui_controlls = pn.Row(self.btn_prev, self.current, self.image_count, self.btn_next, align="center", height=50)
        self._image = pn.Row(self.get_image_by_index(int(self.current.value)-1), align="center")
        self.gui = pn.Column(self.gui_controlls, self.image)

        self.btn_prev.on_click(self._previous)
        self.btn_next.on_click(self._next)
        self.current.param.watch(self._number_input, "value")

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, image):
        self._image = image
        self.gui[1] = self._image

    def _next(self, _):
        index = int(self.current.value)
        if index == self.num_images:
            index = 1
        else:
            index += 1
        self.UPDATING = True
        self.current.value = str(index)
        self.UPDATING = False
        self.image = pn.Row(self.get_image_by_index(index-1), align="center")

    def _previous(self, _):
        index = int(self.current.value)
        if index == 1:
            index = self.num_images
        else:
            index -= 1
        self.UPDATING = True
        self.current.value = str(index)
        self.UPDATING = False
        self.image = pn.Row(self.get_image_by_index(index-1), align="center")

    def _number_input(self, _):
        if self.UPDATING:
            return
        index = int(self.current.value)
        self.image = pn.Row(self.get_image_by_index(index-1), align="center")

    def show(self):
        return self.gui

# Cell
class DatasetOverview(Dashboard):
    DESCRIPTOR_DATA = "data"
    DESCRIPTOR_STATS = "stats"

    def __init__(self, dataset: GenericDataset, height: int = 500, width: int = 500):
        """Creates an overview of a dataset"""
        self.dataset = dataset
        super().__init__(height=height, width=width)

    def _generate_dataset_tab(self):
        overview_table = table_from_dataframe(getattr(self.dataset, self.DESCRIPTOR_DATA), width=self.width, height=self.height)
        return overview_table

    def _generate_datset_stats_tab(self):
        overview_table = table_from_dataframe(getattr(self.dataset, self.DESCRIPTOR_STATS), width=self.width, height=self.height)
        return overview_table

    def build_gui(self):
        dataset_tab = self._generate_dataset_tab()
        dataset_stats_tab = self._generate_datset_stats_tab()
        self.gui = pn.Tabs(("Dataset overview", dataset_tab), ("Dataset stats overview", dataset_stats_tab), align="start")

    def show(self):
        return self.gui

# Cell
class MultiDatasetOverview(Dashboard):
    DESCRIPTOR_DATA = "stats"

    def __init__(self, datasets: Union[List[GenericDataset], ObservableList], height=100, width=1000, with_del_button=False):
        self.datasets = datasets if isinstance(datasets, ObservableList) else ObservableList(datasets)
        self.datasets.register_callback(self.update_table)
        self.with_del_button = with_del_button
        super().__init__(width=width, height=height)

    def create_overview_df(self):
        return pd.concat([getattr(dataset, self.DESCRIPTOR_DATA) for dataset in self.datasets]) if len(self.datasets) > 0 else pd.DataFrame()

    def build_gui(self):
        self.delete_button = pnw.Button(name="Delete", width=self.width, height=25)
        self.overview_table = table_from_dataframe(self.create_overview_df(), height=self.height-25)
        if self.with_del_button:
            self.delete_button.on_click(self.delete_entry)
            self.gui = pn.Column(self.delete_button, self.overview_table)
        else:
            self.gui = pn.Column(self.overview_table)

    def delete_entry(self, clicks):
        selection = self.overview_table.selection
        self.datasets.list = [dataset for index, dataset in enumerate(self.datasets) if index not in selection]

    def update_table(self, event):
        self.overview_table.value = self.create_overview_df()
        self.overview_table.height = height=self.height-25

    def show(self):
        return self.gui

# Cell
class DatasetComparison(Dashboard):
    DESCRIPTOR_DATA = "data"
    DESCRIPTOR_STATS = "stats"

    def _get_descriptor_for_all_datasets(self, descriptor_name):
        return [getattr(dataset, descriptor_name) for dataset in self.datasets]

    def __init__(self, datasets: List[GenericDataset], height: int = 500, width: int = 500):
        """Creates an overview of a dataset"""
        self.datasets = datasets
        super().__init__(height=height, width=width)

    def _generate_dataset_tab(self):
        overview_table = table_from_dataframe(self._get_descriptor_for_all_datasets(self.DESCRIPTOR_DATA), width=self.width, height=self.height)
        return pn.Column(*overview_table)

    def _generate_datset_stats_tab(self):
        overview_table = table_from_dataframe(self._get_descriptor_for_all_datasets(self.DESCRIPTOR_STATS), width=self.width, height=self.height)
        return pn.Column(*overview_table)

    def build_gui(self):
        dataset_tab = self._generate_dataset_tab()
        dataset_stats_tab = self._generate_datset_stats_tab()
        self.gui = pn.Tabs(("Dataset overview", dataset_tab), ("Dataset stats overview", dataset_stats_tab), align="start")

    def show(self):
        return self.gui

# Cell
class DatasetFilter(Dashboard, ABC):
    DESCRIPTOR_DATA = "data"

    def __init__(self, dataset: GenericDataset, columns: Optional[List[str]] = None, height: int = 500, width: int = 500, filter_width: Optional[int] = None, filter_height: Optional[int] = None, n_cols: int = None):
        self.dataset = dataset
        self.columns = columns if columns is not None else getattr(self.dataset, self.DESCRIPTOR_DATA).columns
        self.n_cols = n_cols if n_cols is not None else ceil(len(self.columns)**0.5)
        self.n_rows = (len(self.columns)//self.n_cols) + min(1, len(self.columns)%self.n_cols)
        self.filter_height = int(height/self.n_rows) if filter_height is None else filter_height
        self.filter_width = int(width/self.n_cols) if filter_width is None else filter_width
        self.filters = []
        self.UPDATING = False
        super().__init__(height=height, width=width)

    def build_gui(self):
        """All filters used below need to have two functions get_selection and update_with_mask."""
        data_selection = getattr(self.dataset, self.DESCRIPTOR_DATA)[self.columns]
        self.generate_filters(data_selection)
        # put the images in the grid
        self.gui = pn.GridSpec(ncols=self.n_cols, nrows=self.n_rows, width=self.width, height=self.height)
        for index, gui_filter in enumerate(self.filters):
            self.gui[index//self.n_cols, index%self.n_cols] = gui_filter.show()
        # hook all control elements to the update functions
        for single_filter in self.filters:
            single_filter.register_callback(self.update_plots)

    @abstractmethod
    def generate_filters(self, dataselection):
        """Write handler for the different column types of the datagrame."""
        pass

    def _update_plots(self, current_selection):
        mask = np.array(self.get_selection())
        final_mask = np.logical_or(mask, current_selection)
        for single_filter in self.filters:
            single_filter.update_with_mask(final_mask)

    def update_plots(self, event, old=None, new=None):
        if self.UPDATING:
            return
        else:
            self.UPDATING = True
            self._update_plots(event)
            self.UPDATING = False

    def show(self):
        return self.gui

    def get_selection(self):
        mask = self.filters[0].get_selection()
        for single_filter in self.filters[1:]:
            mask = np.logical_and(mask, single_filter.get_selection())
        return mask

    def register_callback(self, callback):
        """Register callback to every underlying filter"""
        for filter in self.filters:
            filter.register_callback(callback)

# Cell
class DatasetFilterWithRangeSliderAndMultiSelect(DatasetFilter):
    def generate_filters(self, data_selection):
        # generate filters
        for column in data_selection.columns:
            if pd.api.types.is_numeric_dtype(data_selection[column]):
                self.filters.append(RangeFilter(data_selection[column].values, column, height=self.filter_height, width=self.filter_width))
            elif pd.api.types.is_categorical_dtype(data_selection[column]) or pd.api.types.is_string_dtype(data_selection[column]):
                self.filters.append(CategoricalFilter(data_selection[column].values, column, height=self.filter_height, width=self.filter_width))

# Cell
class ScatterDatasetFilter(DatasetFilter):
    def __init__(self, dataset: GenericDataset, columns: Optional[List[str]] = None, height: int = 500, width: int = 500, filter_width: Optional[int] = None, filter_height: Optional[int] = None, n_cols: int = None):
        super().__init__(dataset, columns, height, width, filter_width, filter_height, n_cols)
        self.scatter_filter = None

    def build_gui(self):
        """All filters used below need to have two functions get_selection and update_with_mask."""
        data_selection = getattr(self.dataset, self.DESCRIPTOR_DATA)[self.columns]
        self.generate_filters(data_selection)
        # put the images in the grid
        self.categorical_grid = pn.GridSpec(ncols=self.n_cols, nrows=self.n_rows, width=self.width, height=self.height//2)
        for index, gui_filter in enumerate(self.filters):
            self.categorical_grid[index//self.n_cols, index%self.n_cols] = gui_filter.show()
        # hook all control elements to the update functions
        for single_filter in self.filters:
            single_filter.register_callback(self.update_plots)
        # add the scatter filter
        self.scatter_filter.register_callback(self.update_plots)
        self.gui = pn.Column(self.categorical_grid, self.scatter_filter.show())

    def generate_filters(self, data_selection):
        # generate filters
        numeric_cols = []
        for column in data_selection.columns:
            if pd.api.types.is_numeric_dtype(data_selection[column]):
                numeric_cols.append(column)
            elif pd.api.types.is_categorical_dtype(data_selection[column]) or pd.api.types.is_string_dtype(data_selection[column]):
                self.filters.append(CategoricalFilter(data_selection[column].values, column, height=self.filter_height, width=self.filter_width))
        # generate generic scatter selector
        self.scatter_filter = GenericMulitScatterFilter(data_selection[numeric_cols], height=self.height//2)

# Cell
class DatasetGenerator(Dashboard):
    DESCRIPTOR_DATA = "data"
    DESCRIPTOR_STATS = "stats"

    DATASET_FILTER_COLUMNS = None
    DATASET_FILTER = DatasetFilterWithRangeSliderAndMultiSelect
    MULTI_DATASET_OVERVIEW = MultiDatasetOverview
    DATASET_OVERVIEW = DatasetOverview

    def __init__(self, dataset, width=500, height=500):
        self.base_dataset = dataset
        self.created_datasets = ObservableList([])
        super().__init__(width, height)

    def build_gui(self):
        self.dataset_filter = self.DATASET_FILTER(self.base_dataset, columns=self.DATASET_FILTER_COLUMNS, width=self.width, height=self.height-50)
        self.dataset_filter_create_dataset_button = pnw.Button(name="Create", height=50)
        self.dataset_filter_create_dataset_button.on_click(self.create_dataset)
        self.dataset_filter_with_export = pn.Column(pn.Row(self.dataset_filter.show(), align="center"), pn.Row(self.dataset_filter_create_dataset_button, align="center"))

        self.created_datasets_overview = self.MULTI_DATASET_OVERVIEW(self.created_datasets, with_del_button=True, height=150, width=self.width)
        self.selected_dataset_overview = self.DATASET_OVERVIEW(self.base_dataset, height=self.height-250, width=self.width)
        self.export_gui = self.create_export_gui()
        self.datasets_overview = pn.Column(pn.Row(self.created_datasets_overview.gui, align="center"), pn.Row(self.selected_dataset_overview.gui, align="center"), pn.Row(self.export_gui, align="center"))
        self.created_datasets_overview.overview_table.param.watch(self.update_dataset_overview, "selection")

        self.gui = pn.Tabs(("Dataset Filter", self.dataset_filter_with_export), ("Dataset Overview", self.datasets_overview))

    def create_export_gui(self):
        self.export_path = pnw.TextInput(name="Export path", value="datasets", height=50)
        self.export_button = pnw.Button(name="Export", align="end", height=50)
        self.export_button.on_click(self.export_datasets)

        export_dataset_name = "" if len(self.created_datasets) == 0 else self.created_datasets[self.export_dataset_overview.selection[0]].name
        export_description_name = "" if len(self.created_datasets) == 0 else self.created_datasets[self.export_dataset_overview.selection[0]].description
        self.export_name_input = pnw.TextInput(name="Dataset name", value=export_dataset_name, height=50)
        self.export_name_input.param.watch(self.change_dataset_name, "value")
        self.export_description_input = pnw.TextAreaInput(name="Description", value=export_description_name, height=50)
        self.export_description_input.param.watch(self.change_dataset_description, "value")
        return pn.Column(pn.Row(self.export_name_input, self.export_description_input), pn.Row(self.export_path, self.export_button))

    def change_dataset_name(self, event):
        index = self.created_datasets_overview.overview_table.selection[0]
        self.created_datasets[index].name = self.export_name_input.value

    def change_dataset_description(self, event):
        index = self.created_datasets_overview.overview_table.selection[0]
        self.created_datasets[index].description = self.export_description_input.value

    def update_dataset_overview(self, event):
        self.selected_dataset_overview = self.DATASET_OVERVIEW(self.created_datasets[event.new[0]], height=self.height-350)
        self.datasets_overview[1] = self.selected_dataset_overview.show()
        self.export_name_input.value = self.created_datasets[event.new[0]].name
        self.export_description_input.value = self.created_datasets[event.new[0]].description

    def create_dataset(self, clicks):
        mask = self.dataset_filter.get_selection()
        new_sub_dataset = self.base_dataset.create_new_from_mask(self.base_dataset, mask)
        self.created_datasets.append(new_sub_dataset)

    def export_datasets(self, clicks):
        export_path = self.export_path.value
        if not os.path.isdir(export_path):
            os.makedirs(export_path)
        for dataset in self.created_datasets:
            dataset.save(export_path)

    def show(self):
        return self.gui