from typing import Tuple
import torch

def reshape_for_broadcast(freqs_cis: torch.Tensor, x: torch.Tensor):
    """
    Helper function to reshape frequency tensor to have the same shape as the target tensor 'x'
    for the purpose of broadcasting the frequency tensor during element-wise operations.

    Args:
        freqs_cis (torch.Tensor): Frequency tensor to be reshaped.
        x (torch.Tensor): Target tensor for broadcasting compatibility.

    Returns:
        torch.Tensor: Reshaped frequency tensor.

    Raises:
        AssertionError: If the frequency tensor doesn't match the expected shape.
        AssertionError: If the target tensor 'x' doesn't have the expected number of dimensions.
    """
    ndim = x.ndim
    assert 0 <= 1 < ndim
    assert freqs_cis.shape == (x.shape[1], x.shape[-1])
    shape = [d if i == 1 or i == ndim - 1 else 1 for i, d in enumerate(x.shape)]
    return freqs_cis.view(shape)

def apply_rotary_emb(
    query: torch.Tensor,
    key: torch.Tensor,
    head_dim: int,
    max_seq_len: int,
    theta: float = 10000.0,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Apply rotary embeddings to input tensors using the given frequency tensor.

    This function applies rotary embeddings to the given query and key tensors. The rotation to each token
    embedding is a function of that token's position in the sequence, head_dim, and theta.
    The input tensors are reshaped as complex numbers to simplify your implementation.

    Args:
        query (torch.Tensor): Query tensor to apply rotary embeddings.
                              Shape: (batch_size, seqlen, n_local_heads, self.head_dim)
        key (torch.Tensor): Key tensor to apply rotary embeddings.
                              Shape: (batch_size, seqlen, n_local_kv_heads, self.head_dim)
        head_dim (int): Dimension of each attention head.
        max_seq_len (int): Maximum sequence length supported by model.
    Returns:
        Tuple[torch.Tensor, torch.Tensor]: Tuple of modified query tensor and key tensor with rotary embeddings.
    """

    _, seqlen, _, _ = query.shape
    device = query.device
    # todo
    #
    # Please refer to slide 22 in https://phontron.com/class/anlp2024/assets/slides/anlp-05-transformers.pdf
    # and Section 3 in https://arxiv.org/abs/2104.09864.

    # reshape xq and xk to match the complex representation
    query_real, query_imag = query.float().reshape(query.shape[:-1] + (-1, 2)).unbind(-1)
    key_real, key_imag = key.float().reshape(key.shape[:-1] + (-1, 2)).unbind(-1)
    # This separates each query/key vector into its odd and even indices (assuming *one-indexing*).
    # query_real contains q_1, q_3, q_5, ... and query_imag contains q_2, q_4, q_6, ...

    # First, compute the trigonometric values in the second and fourth columns in
    # slide 22 (linked above).

    # Then, combine these trigonometric values with the tensors query_real, query_imag,
    # key_real, and key_imag.

    #raise NotImplementedError
    def calculate_rotary_embedding_angles(seq_len, head_dim, device):
        # Create a range vector for the dimensions
        dim_range = torch.arange(head_dim, device=device)
        # Calculate the angles theta_i for each dimension
        theta_i = theta ** (-2 * dim_range / head_dim).float()
        # Create a range vector for the positions
        position = torch.arange(seq_len, device=device).float()
        # Multiply the position by theta_i to get the position-specific angles
        angles = position[:, None] * theta_i[None, :]
        # Compute the sine and cosine values for these angles
        sin_values = torch.sin(angles)
        cos_values = torch.cos(angles)
        return cos_values, sin_values
    cos,sin = calculate_rotary_embedding_angles(seqlen,query_real.shape[-2],device)
    query_out_real = cos * query_real - sin * query_imag
    query_out_imag = sin * query_real + cos * query_imag
    key_out_real = cos * key_real - sin * key_imag
    key_out_imag = sin * key_real + cos * key_imag



    # Assuming query_real and query_imag are the real and imaginary parts obtained from the query tensor
    # And you want to interleave them back into a single tensor named query_out

    # Correct combination code
    query_out = torch.cat((query_real.unsqueeze(-1), query_imag.unsqueeze(-1)), dim=-1)
    query_out = query_out.flatten(start_dim=0, end_dim=-3).view(query.shape)

    # Do the same for key_real and key_imag into key_out
    key_out = torch.cat((key_real.unsqueeze(-1), key_imag.unsqueeze(-1)), dim=-1)
    key_out = key_out.flatten(start_dim=0, end_dim=-3).view(key.shape)

    return query_out, key_out