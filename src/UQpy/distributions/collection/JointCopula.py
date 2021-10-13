from types import MethodType
from typing import Union

import numpy as np
from beartype import beartype

from UQpy.distributions.baseclass import Copula
from UQpy.distributions.baseclass import (
    DistributionContinuous1D,
    DistributionND,
    DistributionDiscrete1D,
)


class JointCopula(DistributionND):
    """
    Define a joint distribution from a list of marginals and a copula to introduce dependency. ``JointCopula`` is a
    child class of ``DistributionND``.

    **Inputs:**

    * **marginals** (`list`):
        `list` of ``DistributionContinuous1D`` or ``DistributionDiscrete1D`` objects that define the marginals

    * **copula** (`object`):
        object of class ``Copula``

    A ``JointCopula`` distribution may possess a ``cdf``, ``pdf`` and ``log_pdf`` methods if the copula allows for it
    (i.e., if the copula possesses the necessary ``evaluate_cdf`` and ``evaluate_pdf`` methods).

    The parameters of the distribution are only stored as attributes of the marginals/copula objects. However, the
    ``get_parameters`` and ``update_parameters`` methods can still be used for the joint. Note that each parameter of
    the joint is assigned a unique string identifier as `key_index` - where `key` is the parameter name and `index` the
    index of the marginal (e.g., location parameter of the 2nd marginal is identified as `loc_1`); and `key_c` for
    copula parameters.

    """

    @beartype
    def __init__(
        self,
        marginals: Union[list[DistributionContinuous1D], list[DistributionDiscrete1D]],
        copula: Copula,
    ):
        super().__init__()
        self.ordered_parameters = []
        for i, m in enumerate(marginals):
            self.ordered_parameters.extend(
                [key + "_" + str(i) for key in m.ordered_parameters]
            )
        self.ordered_parameters.extend(
            [key + "_c" for key in copula.ordered_parameters]
        )

        # Check and save the marginals
        self.marginals = marginals
        if not (
            isinstance(self.marginals, list)
            and all(
                isinstance(d, (DistributionContinuous1D, DistributionDiscrete1D))
                for d in self.marginals
            )
        ):
            raise ValueError(
                "Input marginals must be a list of 1d continuous Distribution objects."
            )

        # Check the copula. Also, all the marginals should have a cdf method
        self.copula = copula
        if not isinstance(self.copula, Copula):
            raise ValueError("The input copula should be a Copula object.")
        if not all(hasattr(m, "cdf") for m in self.marginals):
            raise ValueError(
                "All the marginals should have a cdf method in order to define a joint with copula."
            )
        Copula.check_marginals(marginals=self.marginals)

        # Check if methods should exist, if yes define them bound them to the object
        if hasattr(self.copula, "evaluate_cdf"):

            def joint_cdf(dist, x):
                x = dist.check_x_dimension(x)
                # Compute cdf of independent marginals
                unif = np.array(
                    [marg.cdf(x[:, ind_m]) for ind_m, marg in enumerate(dist.marginals)]
                ).T
                # Compute copula
                cdf_val = dist.copula.evaluate_cdf(unit_uniform_samples=unif)
                return cdf_val

            self.cdf = MethodType(joint_cdf, self)

        if all(hasattr(m, "pdf") for m in self.marginals) and hasattr(
            self.copula, "evaluate_pdf"
        ):

            def joint_pdf(dist, x):
                x = dist.check_x_dimension(x)
                # Compute pdf of independent marginals
                pdf_val = np.prod(
                    np.array(
                        [
                            marg.pdf(x[:, ind_m])
                            for ind_m, marg in enumerate(dist.marginals)
                        ]
                    ),
                    axis=0,
                )
                # Add copula term
                unif = np.array(
                    [marg.cdf(x[:, ind_m]) for ind_m, marg in enumerate(dist.marginals)]
                ).T
                c_ = dist.copula.evaluate_pdf(unit_uniform_samples=unif)
                return c_ * pdf_val

            self.pdf = MethodType(joint_pdf, self)

        if all(hasattr(m, "log_pdf") for m in self.marginals) and hasattr(
            self.copula, "evaluate_pdf"
        ):

            def joint_log_pdf(dist, x):
                x = dist.check_x_dimension(x)
                # Compute pdf of independent marginals
                logpdf_val = np.sum(
                    np.array(
                        [
                            marg.log_pdf(x[:, ind_m])
                            for ind_m, marg in enumerate(dist.marginals)
                        ]
                    ),
                    axis=0,
                )
                # Add copula term
                unif = np.array(
                    [marg.cdf(x[:, ind_m]) for ind_m, marg in enumerate(dist.marginals)]
                ).T
                c_ = dist.copula.evaluate_pdf(unit_uniform_samples=unif)
                return np.log(c_) + logpdf_val

            self.log_pdf = MethodType(joint_log_pdf, self)

    def get_parameters(self):
        """
        Return the parameters of a ``distributions`` object.

        To update the parameters of a ``JointIndependent`` or a ``JointCopula`` distribution, each parameter is assigned
        a unique string identifier as `key_index` - where `key` is the parameter name and `index` the index of the
        marginal (e.g., location parameter of the 2nd marginal is identified as `loc_1`).

        **Output/Returns:**

        * (`dict`):
            Parameters of the distribution.

        """
        params = {}
        for i, m in enumerate(self.marginals):
            for key, value in m.get_parameters().items():
                params[key + "_" + str(i)] = value
        for key, value in self.copula.get_parameters().items():
            params[key + "_c"] = value
        return params

    def update_parameters(self, **kwargs):
        """
        Update the parameters of a ``distributions`` object.

        To update the parameters of a ``JointIndependent`` or a ``JointCopula`` distribution, each parameter is assigned
        a unique string identifier as `key_index` - where `key` is the parameter name and `index` the index of the
        marginal (e.g., location parameter of the 2nd marginal is identified as `loc_1`).

        **Input:**

        * keyword arguments:
            Parameters to be updated

        """
        # check arguments
        all_keys = self.get_parameters().keys()
        # update the marginal parameters
        for key_indexed, value in kwargs.items():
            if key_indexed not in all_keys:
                raise ValueError("Unrecognized keyword argument " + key_indexed)
            key_split = key_indexed.split("_")
            key, index = "_".join(key_split[:-1]), key_split[-1]
            if index == "c":
                self.copula.parameters[key] = value
            else:
                self.marginals[int(index)].parameters[key] = value
