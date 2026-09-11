ERROR_FEEDBACK = {
    None: "做对了。继续保持这个计算节奏。",
    "carry_error": "你可能在进位这一步出了问题。请先算个位，满十以后把十位上的数记得进到下一位。",
    "calculation_error": "结果还不对。建议把两位数拆成十位和个位分别计算，再把两部分结果相加。",
    "invalid_answer": "我没有识别到有效数字，请重新填写答案。",
}


def feedback_for(error_type):
    return ERROR_FEEDBACK.get(error_type, ERROR_FEEDBACK["calculation_error"])
