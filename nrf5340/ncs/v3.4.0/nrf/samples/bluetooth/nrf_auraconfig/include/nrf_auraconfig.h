/*
 * Copyright (c) 2024 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#ifndef _NRF_AURACONFIG_H_
#define _NRF_AURACONFIG_H_

#include <zephyr/net_buf.h>


/**
 * @defgroup auraconfig nRF Auraconfig
 * @brief nRF Auraconfig
 *
 * @{
 */

 /**
 * @brief Main function for the Auraconfig sample.
 */
void nrf_auraconfig_main(void);

// modified code
void stream_frame_send(struct net_buf *audio_kor, struct net_buf *audio_eng);
/** @} */

#endif /* _NRF_AURACONFIG_H_ */

