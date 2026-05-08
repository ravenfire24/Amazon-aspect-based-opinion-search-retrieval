def precision_at_k(
    relevant,
    retrieved,
    k
):

    retrieved_k = retrieved[:k]

    relevant_count = len(
        set(retrieved_k).intersection(
            set(relevant)
        )
    )

    return relevant_count / k