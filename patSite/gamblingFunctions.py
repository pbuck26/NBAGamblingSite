def getTeamStr(dictionary, number):
    for key, value in dictionary.items():  # for name, age in dictionary.iteritems():  (for Python 2.x)
        if value == number:
            #print(key)
            return key

def getImpliedProbability(line):
    if line > 0:
        prob = 100/(line + 100)
        return prob
    else:
        prob = abs(line)/(abs(line) + 100)
        return prob

def getPayout(odds, wager):
    if odds > 0:
        payout = (wager*odds)/100
        return payout
    else:
        payout = (wager*100)/abs(odds)
        return payout

