# pylint: disable=missing-docstring,protected-access
import unittest
from unittest.mock import Mock

import numpy as np

from Orange.data import Table, Domain
from Orange.widgets.data.owneighbors import OWNeighbors, METRICS
from Orange.widgets.tests.base import WidgetTest, ParameterMapping


class TestOWNeighbors(WidgetTest):
    def setUp(self):
        self.widget = self.create_widget(OWNeighbors,
                                         stored_settings={"auto_apply": False})
        self.iris = Table("iris")

    def test_input_data(self):
        """Check widget's data with data on the input"""
        widget = self.widget
        self.assertEqual(widget.data, None)
        self.send_signal(widget.Inputs.data, self.iris)
        self.assertEqual(widget.data, self.iris)

    def test_input_data_disconnect(self):
        """Check widget's data after disconnecting data on the input"""
        widget = self.widget
        self.send_signal(widget.Inputs.data, self.iris)
        self.assertEqual(widget.data, self.iris)
        self.send_signal(widget.Inputs.data, None)
        self.assertEqual(widget.data, None)

    def test_input_reference(self):
        """Check widget's reference with reference on the input"""
        widget = self.widget
        self.assertEqual(widget.reference, None)
        self.send_signal(widget.Inputs.reference, self.iris)
        self.assertEqual(widget.reference, self.iris)

    def test_input_reference_disconnect(self):
        """Check reference after disconnecting reference on the input"""
        widget = self.widget
        self.send_signal(widget.Inputs.data, self.iris)
        self.send_signal(widget.Inputs.reference, self.iris)
        self.assertEqual(widget.reference, self.iris)
        self.send_signal(widget.Inputs.reference, None)
        self.assertEqual(widget.reference, None)
        widget.apply_button.button.click()
        self.assertIsNone(self.get_output("Neighbors"))

    def test_output_neighbors(self):
        """Check if neighbors are on the output after apply"""
        widget = self.widget
        self.assertIsNone(self.get_output("Neighbors"))
        self.send_signal(widget.Inputs.data, self.iris)
        self.send_signal(widget.Inputs.reference, self.iris[:10])
        widget.apply_button.button.click()
        self.assertIsNotNone(self.get_output("Neighbors"))
        self.assertIsInstance(self.get_output("Neighbors"), Table)

    def test_settings(self):
        """Check neighbors for various distance metrics"""
        widget = self.widget
        settings = [
            ParameterMapping("", widget.controls.distance_index, METRICS),
            ParameterMapping("", widget.controls.n_neighbors)]
        for setting in settings:
            for val in setting.values:
                self.send_signal(widget.Inputs.data, self.iris)
                self.send_signal(widget.Inputs.reference, self.iris[:10])
                setting.set_value(val)
                widget.apply_button.button.click()
                if METRICS[widget.distance_index][0] != "Jaccard" \
                        and widget.n_neighbors != 0:
                    self.assertIsNotNone(self.get_output("Neighbors"))

    def test_exclude_reference(self):
        """Check neighbors when reference is excluded"""
        widget = self.widget
        reference = self.iris[:5]
        self.send_signal(widget.Inputs.data, self.iris)
        self.send_signal(widget.Inputs.reference, reference)
        self.exclude_reference = True
        widget.apply_button.button.click()
        neighbors = self.get_output(widget.Outputs.data)
        for inst in reference:
            self.assertNotIn(inst, neighbors)

    def test_include_reference(self):
        """Check neighbors when reference is included"""
        widget = self.widget
        widget.controls.exclude_reference.setChecked(False)
        reference = self.iris[:5]
        self.send_signal(widget.Inputs.data, self.iris)
        self.send_signal(widget.Inputs.reference, reference)
        widget.apply_button.button.click()
        neighbors = self.get_output("Neighbors")
        for inst in reference:
            self.assertIn(inst, neighbors)

    def test_similarity(self):
        widget = self.widget
        reference = self.iris[:10]
        self.send_signal(widget.Inputs.data, self.iris)
        self.send_signal(widget.Inputs.reference, reference)
        widget.apply_button.button.click()
        neighbors = self.get_output("Neighbors")
        self.assertEqual(self.iris.domain.attributes,
                         neighbors.domain.attributes)
        self.assertEqual(self.iris.domain.class_vars,
                         neighbors.domain.class_vars)
        self.assertIn("distance", neighbors.domain)
        self.assertTrue(all(100 >= ins["distance"] >= 0 for ins in neighbors))

    def test_missing_values(self):
        widget = self.widget
        data = Table("iris")
        reference = data[:3]
        data.X[0:10, 0] = np.nan
        self.send_signal(widget.Inputs.data, self.iris)
        self.send_signal(widget.Inputs.reference, reference)
        widget.apply_button.button.click()
        self.assertIsNotNone(self.get_output("Neighbors"))

    def test_labels(self):
        """Check labels are updated when data is received"""
        widget = self.widget
        data = Table("iris")
        self.send_signal(widget.Inputs.data, data[:10])
        self.assertIn("10", widget.data_info_label.text())
        self.send_signal(widget.Inputs.reference, data[:12])
        self.assertIn("12", widget.reference_info_label.text())
        self.send_signal(widget.Inputs.reference, data[:15])
        self.assertIn("15", widget.reference_info_label.text())
        self.send_signal(widget.Inputs.data, None)
        self.assertNotIn("10", widget.data_info_label.text())
        self.assertIn("15", widget.reference_info_label.text())
        self.send_signal(widget.Inputs.reference, None)
        self.assertNotIn("15", widget.reference_info_label.text())

    def test_compute_distances_apply_called(self):
        """Check compute distances and apply are called when receiving signal"""
        widget = self.widget
        cdist = widget.compute_distances = Mock()
        apply = widget.apply = Mock()
        data = Table("iris")
        self.send_signal(widget.Inputs.data, data)
        cdist.assert_called()
        apply.assert_called()
        cdist.reset_mock()
        apply.reset_mock()

        self.send_signal(widget.Inputs.reference, data[:10])
        cdist.assert_called()
        apply.assert_called()
        cdist.reset_mock()
        apply.reset_mock()

        self.send_signals([(widget.Inputs.data, data),
                           (widget.Inputs.reference, data[:10])])
        self.assertEqual(cdist.call_count, 1)
        self.assertEqual(apply.call_count, 1)

    def test_compute_distances_calls_distance(self):
        widget = self.widget
        widget.distance_index = 2
        dists = np.random.random((5, 10))
        distance = Mock(return_value=dists)
        try:
            orig_metrics = METRICS[widget.distance_index]
            METRICS[widget.distance_index] = ("foo", distance)
            data = Table("iris")
            data, refs = data[:10], data[-5:]
            self.send_signals([(widget.Inputs.data, data),
                               (widget.Inputs.reference, refs)])
            d1, d2 = distance.call_args[0]
            np.testing.assert_almost_equal(d1.X, data.X)
            np.testing.assert_almost_equal(d2.X, refs.X)
            np.testing.assert_almost_equal(widget.distances, dists.min(axis=1))
        finally:
            METRICS[widget.distance_index] = orig_metrics

    def test_compute_distances_distance_no_data(self):
        widget = self.widget
        distance = Mock()
        try:
            orig_metrics = METRICS[widget.distance_index]
            METRICS[widget.distance_index] = ("foo", distance)
            data = Table("iris")
            data, refs = data[:10], data[-5:]
            self.send_signals([(widget.Inputs.data, data),
                               (widget.Inputs.reference, None)])
            distance.assert_not_called()
            self.assertIsNone(widget.distances)
            self.send_signal(widget.Inputs.data, data)
            distance.assert_not_called()
            self.assertIsNone(widget.distances)
            self.send_signals([(widget.Inputs.data, None),
                               (widget.Inputs.reference, refs)])
            distance.assert_not_called()
            self.assertIsNone(widget.distances)
            self.send_signals([(widget.Inputs.data, data),
                               (widget.Inputs.reference, None)])
            distance.assert_not_called()
            self.assertIsNone(widget.distances)

            data, refs = data[:0], data[:0]
            self.send_signals([(widget.Inputs.data, data),
                               (widget.Inputs.reference, None)])
            distance.assert_not_called()
            self.assertIsNone(widget.distances)
        finally:
            METRICS[widget.distance_index] = orig_metrics

    def test_compute_indices_with_reference(self):
        widget = self.widget
        # Indices for easier reading: 0  1  2  3  4  5  6  7  8  9 10 11 12
        widget.distances = np.array([4., 1, 7, 0, 5, 2, 4, 0, 2, 2, 2, 9, 8])

        widget.exclude_reference = False
        widget.n_neighbors = 3
        self.assertEqual(sorted(widget._compute_indices()), [1, 3, 7])

        widget.n_neighbors = 1
        self.assertIn(list(widget._compute_indices()), ([3], [7]))

        widget.n_neighbors = 5
        ind = set(widget._compute_indices())
        self.assertEqual(len(ind), 5)
        self.assertTrue({1, 3, 7} < ind)
        self.assertTrue(len({5, 8, 9, 10} & ind) == 2)

        widget.n_neighbors = 100
        self.assertEqual(sorted(widget._compute_indices()), list(range(13)))

        widget.n_neighbors = 13
        self.assertEqual(sorted(widget._compute_indices()), list(range(13)))

        widget.n_neighbors = 14
        self.assertEqual(sorted(widget._compute_indices()), list(range(13)))

        widget.n_neighbors = 12
        self.assertEqual(
            sorted(widget._compute_indices()),
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12])

    def test_compute_indices_without_reference(self):
        widget = self.widget
        # Indices for easier reading: 0  1  2  3  4  5  6  7  8  9 10 11 12
        widget.distances = np.array([4., 1, 7, 0, 5, 2, 4, 0, 2, 2, 2, 9, 8])

        widget.exclude_reference = True
        widget.n_neighbors = 5
        self.assertEqual(sorted(widget._compute_indices()), [1, 5, 8, 9, 10])

        widget.n_neighbors = 1
        self.assertEqual(list(widget._compute_indices()), [1])

        widget.n_neighbors = 3
        ind = set(widget._compute_indices())
        self.assertEqual(len(ind), 3)
        self.assertIn(1, ind)
        self.assertTrue(len({5, 8, 9, 10} & ind) == 2)

        widget.n_neighbors = 100
        self.assertEqual(
            sorted(widget._compute_indices()),
            [0, 1, 2, 4, 5, 6, 8, 9, 10, 11, 12])

        widget.n_neighbors = 11
        self.assertEqual(
            sorted(widget._compute_indices()),
            [0, 1, 2, 4, 5, 6, 8, 9, 10, 11, 12])

        widget.n_neighbors = 12
        self.assertEqual(
            sorted(widget._compute_indices()),
            [0, 1, 2, 4, 5, 6, 8, 9, 10, 11, 12])

        widget.n_neighbors = 10
        self.assertEqual(
            sorted(widget._compute_indices()),
            [0, 1, 2, 4, 5, 6, 8, 9, 10, 12])

    def test_data_with_similarity(self):
        widget = self.widget
        indices = np.array([5, 10, 15, 100])

        data = Table("iris")
        widget.data = data

        widget.distances = np.arange(1000, 1150).astype(float)
        neighbours = widget._data_with_similarity(indices)
        self.assertEqual(neighbours.metas.shape, (4, 1))
        np.testing.assert_almost_equal(
            neighbours.metas.flatten(), indices + 1000)
        np.testing.assert_almost_equal(neighbours.X, data.X[indices])

        domain = data.domain
        domain2 = Domain([domain[2]], domain.class_var, metas=domain[:2])
        data2 = data.transform(domain2)
        widget.data = data2

        widget.distances = np.arange(1000, 1150).astype(float)
        neighbours = widget._data_with_similarity(indices)
        self.assertEqual(len(neighbours.domain.metas), 3)
        self.assertEqual(neighbours.metas.shape, (4, 3))
        np.testing.assert_almost_equal(
            neighbours.get_column_view("distance")[0], indices + 1000)
        np.testing.assert_almost_equal(neighbours.X, data2.X[indices])

    def test_apply(self):
        widget = self.widget
        widget.auto_apply = True
        data = Table("iris")
        indices = np.array([5, 10, 15, 100])

        widget._compute_indices = lambda: \
            indices if widget.distances is not None else None
        self.send_signal(widget.Inputs.data, data)
        self.send_signal(widget.Inputs.reference, data[42:43])
        neigh = self.get_output(widget.Outputs.data)
        np.testing.assert_almost_equal(neigh.X, data.X[indices])
        np.testing.assert_almost_equal(
            neigh.metas.flatten(), widget.distances[indices])

    def test_all_equal_ref(self):
        widget = self.widget
        widget.auto_apply = True

        data = Table("iris")
        self.send_signal(widget.Inputs.data, data)
        self.send_signal(widget.Inputs.reference, data[42:43])

        orig_distances = widget.distances
        widget.distances = np.zeros(len(data), dtype=float)
        widget.apply()
        self.assertTrue(widget.Warning.all_data_as_reference.is_shown())
        self.assertIsNone(self.get_output(widget.Outputs.data))

        widget.distances = orig_distances
        widget.apply()
        self.assertFalse(widget.Warning.all_data_as_reference.is_shown())
        self.assertIsNotNone(self.get_output(widget.Outputs.data))


if __name__ == "__main__":
    unittest.main()