def is_blinking(face, detector, ratio_list, counter, threshold=32, cooldown=10):
    leftUp = face[159]
    leftDown = face[23]
    leftLeft = face[130]
    leftRight = face[243]
    
    vertical_len, _ = detector.findDistance(leftUp, leftDown)
    horizontal_len, _ = detector.findDistance(leftLeft, leftRight)

    if horizontal_len == 0:
        return False, ratio_list, counter

    ratio = (vertical_len / horizontal_len) * 100
    ratio_list.append(ratio)
    if len(ratio_list) > 5:
        ratio_list.pop(0)
    ratio_avg = sum(ratio_list) / len(ratio_list)

    blink_detected = False
    if ratio_avg < threshold and counter == 0:
        blink_detected = True
        counter = 1
    if counter != 0:
        counter += 1
        if counter > cooldown:
            counter = 0

    return blink_detected, ratio_list, counter