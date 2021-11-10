import logging
from typing import Union

from UQpy.sampling.latin_hypercube_criteria import Random
from UQpy.utilities.ValidationTypes import PositiveInteger
from UQpy.distributions import *
from UQpy.sampling.latin_hypercube_criteria.baseclass.Criterion import *
import numpy as np
from UQpy.distributions import DistributionContinuous1D, JointIndependent


class LatinHypercubeSampling:
    @beartype
    def __init__(
        self,
        distributions: Union[Distribution, list[Distribution]],
        samples_number: PositiveInteger,
        criterion: Criterion = Random(),
    ):
        """
        Perform Latin hypercube sampling (LHS) of random variables.

        All distributions in :class:`LatinHypercubeSampling` must be independent. :class:`.LatinHypercubeSampling` does
        not generate correlated random variables. Therefore, for multi-variate designs the `distributions` must be a
        list of :class:`.DistributionContinuous1D` objects or an object of the :class:`.JointIndependent` class.


        :param distributions: List of :class:`.Distribution` objects
         corresponding to each random variable.
        :param samples_number: Number of samples to be drawn from each distribution.
        :param criterion: The criterion for pairing the generating sample points. This parameter must be of
         type :class:`.Criterion`.

         Options:

         1. 'Random' - completely random. \n
         2. 'Centered' - points only at the centre. \n
         3. 'MaxiMin' - maximizing the minimum distance between points. \n
         4. 'MinCorrelation' - minimizing the correlation between the points. \n
         5. User-defined criterion class, by providing an implementation of the abstract class :class:`Criterion`
        """
        self.dist_object = distributions
        self.criterion = criterion
        self.samples_number = samples_number
        self.logger = logging.getLogger(__name__)
        self.samples = None
        """ The generated LHS samples."""
        if isinstance(self.dist_object, list):
            self.samples = np.zeros([self.samples_number, len(self.dist_object)])
        elif isinstance(self.dist_object, DistributionContinuous1D):
            self.samples = np.zeros([self.samples_number, 1])
        elif isinstance(self.dist_object, JointIndependent):
            self.samples = np.zeros(
                [self.samples_number, len(self.dist_object.marginals)]
            )

        self.samplesU01 = np.zeros_like(self.samples)
        """The generated LHS samples on the unit hypercube."""

        if self.samples_number is not None:
            self.run(self.samples_number)

    @beartype
    def run(self, samples_number: PositiveInteger):
        """
        Execute the random sampling in the :class:`.LatinHypercubeSampling` class.

        :param samples_number: If the :meth:`run` method is invoked multiple times, the newly generated samples will
         overwrite the existing samples.

        The :meth:`run` method is the function that performs random sampling in the :class:`.LatinHypercubeSampling`
        class. If `samples_number` is provided, the :meth:`run` method is automatically called when the
        :class:`.LatinHypercubeSampling` object is defined. The user may also call the :meth:`run` method directly to
        generate samples. The :meth:`run` method of the :class:`.LatinHypercubeSampling` class cannot be invoked
        multiple times for sample size extension.

        The :meth:`run` method has no returns, although it creates and/or appends the `samples` and `samplesU01`
        attributes of the :class:`.LatinHypercubeSampling` object.
        """
        self.samples_number = samples_number
        self.logger.info("UQpy: Running Latin Hypercube sampling...")
        self.criterion.create_bins(self.samples)

        u_lhs = self.criterion.generate_samples()
        self.samplesU01 = u_lhs

        if isinstance(self.dist_object, list):
            for j in range(len(self.dist_object)):
                if hasattr(self.dist_object[j], "icdf"):
                    self.samples[:, j] = self.dist_object[j].icdf(u_lhs[:, j])

        elif isinstance(self.dist_object, JointIndependent):
            if all(hasattr(m, "icdf") for m in self.dist_object.marginals):
                for j in range(len(self.dist_object.marginals)):
                    self.samples[:, j] = self.dist_object.marginals[j].icdf(u_lhs[:, j])

        elif isinstance(self.dist_object, DistributionContinuous1D):
            if hasattr(self.dist_object, "icdf"):
                self.samples = self.dist_object.icdf(u_lhs)

        self.logger.info("Successful execution of LHS design.")
